# Query Result

The Query Result section lets you analyze chatbot queries within a chosen date range, see which documents were used to
answer them, inspect the queries that hit a specific document, and extract common topics from the query set. This helps
QA, tuning, and root-cause investigation of answer quality.

---

## Main UI components

- **Date range selector**: choose start and end dates to filter queries.
- **Summary / KPIs**: total queries in range, distinct queries, queries with document hits, average response time.
- **Document usage table**: lists documents used by queries with stats (occurrences, avg cosine score, min/max score).
- **Query list panel**: chronological list of queries with metadata (text, user/session id, timestamp, hit documents,
  cosine scores).
- **Document detail view**: when a document row is selected, show all queries that hit that document and details of each
  hit.
- **Topics panel**: extracted topics from the query set with labels, relevance scores, example queries.

---

## 1) View queries submitted to the chatbot from date to date

- Action:
    1. Select a date range with the Date range selector.
    2. Click Apply to load results for that range.
- Display:
    - Summary KPIs update immediately.
    - Query list shows records ordered by timestamp (newest → oldest).
- Interaction:
    - Search/filter queries by keyword, user id, session id, or hit status (hit / no-hit).
    - Pagination or infinite scroll for large result sets.

---

## 2) Document usage statistics across queries

- Purpose: understand how often and how well each document contributes.
- Columns in Document usage table:
    - **Document ID / Title**
    - **Occurrences**: number of times the document appeared in query results.
    - **Avg Cosine**: average cosine similarity when the document appeared.
    - **Min Cosine / Max Cosine**: observed similarity range.
    - **Hit Rate**: proportion of queries that included this document (optional).
- Actions:
    - The table updates after selecting the date range.
    - Sort by Occurrences or Avg Cosine to find frequently used or highly relevant documents.
- Reading hints:
    - High Occurrences but low Avg Cosine → document is returned often but may be weakly relevant.
    - Low Occurrences but high Avg Cosine → document is highly relevant for specific queries.

---

## 3) List queries that hit a specific document

- Action:
    1. Click a document row in the Document usage table.
    2. Open Document detail view (drawer or page).
- Detail view contents:
    - List of queries that hit the document: timestamp, user/session id, query text, cosine score, rank position in
      results.
    - Filters inside the view: e.g., only queries with cosine >= X, or a narrower date sub-range.
    - Link to open full conversation/session context if available.
- Interaction:
    - Export the list to CSV for offline analysis.
    - Flag problematic queries (false positives) for follow-up.

---

## 4) Extract common topics from queries

- Purpose: summarize common user intents and help prioritize content improvements.
- UI behavior:
    - Topics panel updates when date range changes or when you press “Extract Topics”.
    - Each topic displays **label**, **relevance/score**, **# queries in topic**, and **example queries**.
- How it’s generated (user-facing explanation):
    - Topics are derived by clustering query embeddings or using topic modeling; the UI shows computed results.
- Interaction:
    - Click a topic to filter the Query list to queries in that topic.
    - Adjust granularity (number of topics) if the control is available.
    - View top keywords and representative queries for each topic.
- Use cases:
    - Detect popular user needs, prioritize document updates, create intents or FAQs, and identify new or emerging
      issues.

---

## Recommended workflow example

1. Select date range 2025-10-01 → 2025-10-31.
2. Inspect Document usage table → sort by Occurrences to find top 10 documents used.
3. Select a document → open details → filter hits with cosine < 0.3 to find likely false positives.
4. Open Topics panel → review top 5 topics for the month → click topic “billing” to view related queries.
5. If a document is widely used but returns many false positives, consider tuning retriever thresholds or updating
   document content.
