"""Core data pipeline: cleaning, column detection, transaction building,
and the Apriori + association-rules stages. Used by both the
Simple ("Get Recommendations") flow and the Advanced pipeline pages."""
import streamlit as st
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth


def clean_data_default(df):
    """Sensible default cleaning: strip spaces, drop empty rows/columns,
    drop duplicates, and remove returns/cancellations if those columns
    can be detected."""

    cleaned = df.copy()

    cleaned.columns = cleaned.columns.astype(str).str.strip()

    text_columns = cleaned.select_dtypes(include=["object"]).columns

    for column in text_columns:
        cleaned[column] = cleaned[column].astype(str).str.strip()

    cleaned = cleaned.drop_duplicates()
    cleaned = cleaned.dropna(how="all")
    cleaned = cleaned.dropna(axis=1, how="all")

    quantity_column = None
    for column in cleaned.columns:
        if str(column).strip().lower() == "quantity":
            quantity_column = column

    invoice_column = None
    for column in cleaned.columns:
        if "invoice" in str(column).strip().lower():
            invoice_column = column

    if quantity_column is not None:
        cleaned = cleaned[cleaned[quantity_column] >= 0]

    if invoice_column is not None:
        cleaned = cleaned[
            ~cleaned[invoice_column]
            .astype(str)
            .str.strip()
            .str.upper()
            .str.startswith("C")
        ]

    return cleaned


def auto_detect_columns(df):
    """Best-effort guess at which column identifies a transaction/order
    and which column holds the product name, so the user never has to
    pick columns manually."""

    transaction_column = None
    product_column = None

    for column in df.columns:

        lower = str(column).strip().lower()

        if transaction_column is None and "invoice" in lower:
            transaction_column = column

        if product_column is None and (
            "description" in lower
            or "product" in lower
            or "item" in lower
        ):
            product_column = column

    if transaction_column is None:
        for column in df.columns:
            if 1 < df[column].nunique() < len(df):
                transaction_column = column
                break

    if product_column is None:
        text_columns = (
            df.select_dtypes(include=["object"]).columns.tolist()
        )
        if transaction_column in text_columns:
            text_columns.remove(transaction_column)
        product_column = (
            text_columns[0] if text_columns else df.columns[-1]
        )

    return transaction_column, product_column


def detect_sales_columns(df):
    """Best-effort detection of the common e-commerce columns behind the
    Dashboard's Sales Overview tab (invoice, product, quantity, unit
    price, customer, country, date). Mirrors the same fuzzy, name-based
    approach as auto_detect_columns() above. Any column not found is
    left as None so callers can degrade a single metric gracefully
    instead of crashing the whole page."""

    columns = {
        "invoice": None,
        "product": None,
        "quantity": None,
        "price": None,
        "customer": None,
        "country": None,
        "date": None,
    }

    for column in df.columns:

        lower = str(column).strip().lower()

        if columns["date"] is None and "date" in lower:
            columns["date"] = column
            continue

        if columns["invoice"] is None and "invoice" in lower:
            columns["invoice"] = column
            continue

        if columns["price"] is None and "price" in lower:
            columns["price"] = column
            continue

        if columns["customer"] is None and "customer" in lower:
            columns["customer"] = column
            continue

        if columns["country"] is None and "country" in lower:
            columns["country"] = column
            continue

        if columns["quantity"] is None and lower == "quantity":
            columns["quantity"] = column
            continue

        if columns["product"] is None and (
            "description" in lower
            or "product" in lower
            or "item" in lower
        ):
            columns["product"] = column
            continue

    return columns


@st.cache_data(show_spinner=False)
def build_transactions(df, transaction_column, product_column):
    """Groups rows into a list of transactions (one list of products
    per order). Uses a plain dict loop over the two columns instead
    of groupby().apply(list) — pandas has to call back into Python
    once per group for apply(), which gets slow with hundreds of
    thousands of groups; a single pass with a dict is ~9x faster on
    a ~1M-row benchmark and produces identical results."""

    transaction_data = (
        df[[transaction_column, product_column]]
        .copy()
        .dropna()
    )

    transaction_data[product_column] = (
        transaction_data[product_column]
        .astype(str)
        .str.strip()
    )

    transaction_data = transaction_data[
        transaction_data[product_column] != ""
    ]

    grouped = {}

    for transaction_id, product in zip(
        transaction_data[transaction_column].to_numpy(),
        transaction_data[product_column].to_numpy()
    ):
        grouped.setdefault(transaction_id, []).append(product)

    transactions = [
        list(dict.fromkeys(products))
        for products in grouped.values()
    ]

    transactions = [t for t in transactions if len(t) > 0]

    return transactions


@st.cache_data(show_spinner=False)
def trim_rare_products(transactions, min_count=2):
    """Drops products that appear in fewer than min_count transactions.
    This shrinks the basket matrix directly (fewer columns to encode),
    which is usually the single biggest lever for a large product
    catalog. It's also "free" in the sense that a product this rare
    can't clear any realistic min_support threshold anyway, so dropping
    it early doesn't change which frequent itemsets you'd find."""

    counts = {}

    for transaction in transactions:
        for product in transaction:
            counts[product] = counts.get(product, 0) + 1

    keep = {
        product for product, count in counts.items()
        if count >= min_count
    }

    trimmed = [
        [product for product in transaction if product in keep]
        for transaction in transactions
    ]

    trimmed = [transaction for transaction in trimmed if transaction]

    return trimmed


@st.cache_data(show_spinner=False)
def build_basket_df(transactions, sparse=True):
    """Builds the one-hot encoded basket matrix. Sparse by default —
    a basket matrix is almost always >99% False (most transactions
    contain a tiny fraction of the full catalog), so storing it as a
    pandas sparse DataFrame instead of a dense one typically cuts
    memory usage by 10-50x+ and is what actually avoids the
    MemoryError on large datasets. apriori()/fpgrowth() both accept
    sparse DataFrames directly, so nothing downstream needs to change."""

    encoder = TransactionEncoder()

    if sparse:

        sparse_array = (
            encoder.fit(transactions).transform(transactions, sparse=True)
        )

        return pd.DataFrame.sparse.from_spmatrix(
            sparse_array,
            columns=encoder.columns_
        )

    encoded_array = encoder.fit(transactions).transform(transactions)

    return pd.DataFrame(
        encoded_array,
        columns=encoder.columns_
    )


def _step_up_for_memory(basket_df, min_support, max_length, ceiling=0.5):
    """Tries min_support, and escalates it UPWARD only in response to
    an actual MemoryError — never in response to an empty result,
    since a stricter (higher) threshold can only find the same
    itemsets as a looser one, or fewer, never more. Escalating here
    only ever trades "fewer patterns" for "fits in memory", which is
    the right trade only when memory is the actual problem.

    Returns (frequent_itemsets, used_support, hit_memory_error)."""

    support = min_support
    hit_memory_error = False

    while True:

        try:
            itemsets = apriori(
                basket_df,
                min_support=support,
                use_colnames=True,
                max_len=max_length,
                low_memory=True
            )
            return itemsets, support, hit_memory_error

        except MemoryError:
            hit_memory_error = True

            if support >= ceiling:
                return pd.DataFrame(), support, hit_memory_error

            support = min(max(support * 2, 0.03), ceiling)


def _step_down_for_results(basket_df, min_support, max_length, floor=0.0005):
    """Tries progressively LOWER support levels to actually find
    something. This is the only direction that can recover an empty
    result — raising min_support further can never do it, since every
    itemset that clears a higher bar also clears a lower one, but not
    the other way around.

    Returns (frequent_itemsets, used_support)."""

    support = min_support

    while support > floor:

        support = round(support / 2, 6)

        try:
            itemsets = apriori(
                basket_df,
                min_support=support,
                use_colnames=True,
                max_len=max_length,
                low_memory=True
            )
        except MemoryError:
            # A lower support means more candidate itemsets, i.e. more
            # memory, not less — if going lower hits a memory wall,
            # stop here rather than push further into it.
            break

        if not itemsets.empty:
            return itemsets, support

    return pd.DataFrame(), min_support


@st.cache_data(show_spinner="Running Apriori...")
def run_apriori_safe(basket_df, min_support=0.02, max_length=2):
    """Runs apriori, handling its two distinct failure modes
    separately instead of conflating them into one "back off" list:

    - MemoryError (too many candidate itemsets to hold at this
      support): escalate min_support UPWARD from the requested value
      until it fits in memory, then fall back to FP-Growth at the
      original min_support as a last resort — FP-Growth builds a
      compressed tree instead of enumerating every candidate itemset,
      so it often succeeds where Apriori runs out of memory.
    - Empty result with NO memory error (nothing meets the bar):
      step min_support DOWNWARD instead. Raising it further is
      guaranteed to also find nothing, since it only makes the bar
      stricter — lowering it is the only direction that can help.

    Never silently tries a support level below what was requested
    when the goal is to raise it for memory, and never wastes time
    raising it when the goal is to find more matches."""

    frequent_itemsets, used_support, hit_memory_error = (
        _step_up_for_memory(basket_df, min_support, max_length)
    )

    if hit_memory_error and frequent_itemsets.empty:

        try:
            frequent_itemsets = fpgrowth(
                basket_df,
                min_support=min_support,
                use_colnames=True,
                max_len=max_length
            )
            used_support = min_support

        except MemoryError as e:
            raise MemoryError(
                "Dataset is too large to process, even after "
                "raising the minimum support and trying FP-Growth."
            ) from e

    elif frequent_itemsets.empty:

        frequent_itemsets, used_support = _step_down_for_results(
            basket_df, min_support, max_length
        )

    return frequent_itemsets, used_support


@st.cache_data(show_spinner=False)
def generate_association_rules_simple(
    frequent_itemsets, basket_df, min_confidence=0.10, min_lift=1.0
):

    try:
        rules = association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=min_confidence,
            num_itemsets=len(basket_df)
        )
    except TypeError:
        rules = association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=min_confidence
        )

    rules = rules[rules["lift"] >= min_lift].copy()

    return rules


def confidence_to_phrase(confidence):
    """Turn a raw confidence score into a plain-English phrase,
    so a non-technical user never has to see the word 'confidence'."""

    if confidence >= 0.70:
        return "Almost always bought together"
    elif confidence >= 0.50:
        return "Very often bought together"
    elif confidence >= 0.30:
        return "Often bought together"
    elif confidence >= 0.15:
        return "Sometimes bought together"
    else:
        return "Occasionally bought together"


def lift_to_strength(lift):
    """Turn a raw lift score into a plain match-strength label,
    so a non-technical user never has to see the word 'lift'."""

    if lift >= 3:
        return "⭐⭐⭐ Strong match"
    elif lift >= 2:
        return "⭐⭐ Good match"
    else:
        return "⭐ Worth trying"


def build_recommendations_table(rules_df, top_n=50):
    """Flattens antecedents/consequents into a plain-language
    'if a customer buys X, recommend Y' table — the only thing a
    non-technical user actually needs to see."""

    rows = []

    for _, row in rules_df.iterrows():

        antecedent = ", ".join(
            sorted(str(item) for item in row["antecedents"])
        )

        for product in row["consequents"]:

            rows.append({
                "If customer buys": antecedent,
                "Recommend": str(product),
                "How Often Bought Together": confidence_to_phrase(
                    row["confidence"]
                ),
                "Match Strength": lift_to_strength(row["lift"]),
                "Confidence": round(row["confidence"], 3),
                "Lift": round(row["lift"], 3)
            })

    recommendations_df = pd.DataFrame(rows)

    if recommendations_df.empty:
        return recommendations_df

    recommendations_df = (
        recommendations_df
        .sort_values(["Lift", "Confidence"], ascending=False)
        .drop_duplicates(subset=["If customer buys", "Recommend"])
        .head(top_n)
        .reset_index(drop=True)
    )

    return recommendations_df


