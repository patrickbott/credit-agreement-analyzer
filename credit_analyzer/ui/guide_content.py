"""Content for the Getting Started guide."""

from __future__ import annotations

QUICK_START_STEPS: tuple[tuple[str, str, str], ...] = (
    (
        "1",
        "Upload",
        "Use the sidebar to upload a credit agreement PDF, then click "
        "<strong>Index PDF</strong> to process it.",
    ),
    (
        "2",
        "Ask",
        "Type a question in the chat bar or click one of the suggested "
        "questions to get started.",
    ),
    (
        "3",
        "Report",
        "Click <strong>Generate Report</strong> for a full 10-section "
        "analysis with PDF export.",
    ),
)

GUIDE_SECTIONS: tuple[tuple[str, str], ...] = (
    (
        "Uploading a Document",
        "<p>Use the file uploader in the sidebar to select a "
        "credit agreement in PDF format. Scanned documents are supported "
        "(the system uses OCR when needed).</p>"
        "<p>After selecting a file, click <strong>Index PDF</strong>. The app "
        "will run through five processing steps:</p>"
        "<ol>"
        "<li><strong>Extracting text</strong> &mdash; reads every page of the PDF</li>"
        "<li><strong>Detecting structure</strong> &mdash; identifies article and "
        "section boundaries</li>"
        "<li><strong>Parsing definitions</strong> &mdash; builds a glossary of "
        "defined terms</li>"
        "<li><strong>Building embeddings</strong> &mdash; converts text into a "
        "searchable format</li>"
        "<li><strong>Creating search index</strong> &mdash; finalizes the "
        "keyword and semantic indexes</li>"
        "</ol>"
        "<p>Once indexing completes, the sidebar shows document stats "
        "(pages, sections, chunks, and defined terms) and the chat is ready to use. "
        "To remove the current document and upload a different one, click "
        "<strong>Remove Document</strong>.</p>",
    ),
    (
        "Asking Questions",
        "<p>Type any question about the agreement into the chat bar at the "
        "bottom of the screen, or click one of the <strong>suggested questions</strong> "
        "that appear when you first open a document. The system searches the document "
        "for the most relevant passages, then uses an AI model to compose an answer "
        "grounded in the actual text.</p>"
        "<p>Three toggle chips sit below the chat input to control answer behavior:</p>"
        "<ul>"
        "<li><strong>Extended Thinking</strong> &mdash; enables deeper, multi-step "
        "reasoning for complex questions</li>"
        "<li><strong>Show Sources</strong> &mdash; adds inline citation references "
        "linking back to the source sections of the agreement</li>"
        "<li><strong>Commentary</strong> &mdash; includes analytical commentary "
        "alongside the factual answer</li>"
        "</ul>"
        "<p>Each answer includes:</p>"
        "<ul>"
        "<li><strong>Defined terms</strong> &mdash; highlighted words you can "
        "click to see their contractual definition</li>"
        "<li><strong>Context strip</strong> &mdash; a summary bar showing "
        "confidence, chunk count, sections used, and response time</li>"
        "<li><strong>Retrieved context</strong> &mdash; an expandable panel "
        "showing the raw passages the answer is based on</li>"
        "<li><strong>Copy button</strong> &mdash; copies the answer text to your "
        "clipboard</li>"
        "</ul>"
        "<p>The chat supports follow-up questions. Each new question is "
        "automatically interpreted in the context of the conversation so far, "
        "so you can ask &ldquo;What about exceptions to that?&rdquo; without "
        "repeating the topic. You can also edit and retry a previous question "
        "to refine your results.</p>",
    ),
    (
        "Writing Effective Prompts",
        "<p>The more specific your question, the better the answer. "
        "Here are some tips:</p>"
        "<table>"
        "<tr><th style='text-align:left;padding:4px 12px 4px 0;'>Instead of&hellip;</th>"
        "<th style='text-align:left;padding:4px 0;'>Try&hellip;</th></tr>"
        "<tr><td style='padding:4px 12px 4px 0;color:#6B7280;'>"
        "&ldquo;Tell me about covenants&rdquo;</td>"
        "<td style='padding:4px 0;'>"
        "&ldquo;What are the maintenance financial covenants and their "
        "threshold levels?&rdquo;</td></tr>"
        "<tr><td style='padding:4px 12px 4px 0;color:#6B7280;'>"
        "&ldquo;What can the borrower do?&rdquo;</td>"
        "<td style='padding:4px 0;'>"
        "&ldquo;How much incremental debt can the borrower incur under the "
        "credit agreement?&rdquo;</td></tr>"
        "<tr><td style='padding:4px 12px 4px 0;color:#6B7280;'>"
        "&ldquo;Summarize this&rdquo;</td>"
        "<td style='padding:4px 0;'>"
        "&ldquo;Summarize the key terms of the revolving credit "
        "facility&rdquo;</td></tr>"
        "</table>"
        "<p style='margin-top:0.75rem;'><strong>More tips:</strong></p>"
        "<ul>"
        "<li>Reference specific sections or articles when you know them "
        "(e.g., &ldquo;What does Section 7.11 require?&rdquo;)</li>"
        "<li>Ask comparative questions "
        "(e.g., &ldquo;How do the Term A and Term B facilities differ?&rdquo;)</li>"
        "<li>Use follow-up questions to drill deeper into a topic rather than "
        "asking one broad question</li>"
        "<li>Ask for lists or tables when you want structured output "
        "(e.g., &ldquo;List all the conditions precedent&rdquo;)</li>"
        "</ul>",
    ),
    (
        "Generating a Full Report",
        "<p>Click <strong>Generate Report</strong> in the sidebar to open the "
        "section picker. You can select which of the 10 sections to include, "
        "saving time and API calls when you only need specific areas:</p>"
        "<ol>"
        "<li>Transaction Overview</li>"
        "<li>Facility Summary and Pricing</li>"
        "<li>Bank Group</li>"
        "<li>Financial Covenants</li>"
        "<li>Negative Covenants &mdash; Debt Capacity</li>"
        "<li>Negative Covenants &mdash; Liens</li>"
        "<li>Negative Covenants &mdash; Restricted Payments</li>"
        "<li>Negative Covenants &mdash; Investments and Asset Sales</li>"
        "<li>Events of Default and Amendments</li>"
        "<li>Other Notable Provisions</li>"
        "</ol>"
        "<p>Generation typically takes one to two minutes. You can watch each "
        "section appear in real time as it completes. Once finished:</p>"
        "<ul>"
        "<li>Click <strong>Download PDF</strong> to save the full report</li>"
        "<li>Use the section navigation on the left to jump between sections</li>"
        "<li>Click the refresh icon on any section to regenerate just that part</li>"
        "<li>Use the copy button to copy a section to your clipboard</li>"
        "</ul>"
        "<p>After a report is generated, the sidebar shows <strong>View Report</strong> "
        "to reopen it and <strong>New Report</strong> to generate a fresh one.</p>",
    ),
    (
        "Browsing Definitions",
        "<p>Credit agreements contain hundreds of defined terms. The app makes "
        "these easy to explore in two ways:</p>"
        "<ul>"
        "<li><strong>Definitions dialog</strong> &mdash; click "
        "<strong>Definitions</strong> in the sidebar to open a searchable list "
        "of all defined terms. Type a keyword to filter "
        "(e.g., &ldquo;EBITDA&rdquo; or &ldquo;Applicable Rate&rdquo;).</li>"
        "<li><strong>Inline highlights</strong> &mdash; defined terms appear "
        "highlighted in chat answers. Click any highlighted term to see its "
        "definition in a tooltip. Press Escape or click outside to dismiss.</li>"
        "</ul>",
    ),
)
