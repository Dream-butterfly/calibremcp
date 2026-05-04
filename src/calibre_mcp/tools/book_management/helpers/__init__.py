"""
Helpers for book search and management.

These modules contain pure or nearly-pure functions extracted from the
monolithic search_books_helper in book_tools.py. Each module handles
one concern:
- query_builder.py: Parse search text, build search queries, assemble filters dict
- filter_assembler.py: Pop filters, recompute search_text, build get_all_filters
- result_formatter.py: Format search results into response dict, table output
"""
