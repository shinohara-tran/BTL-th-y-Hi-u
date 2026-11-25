"""Unit tests for EdgarHtmlParser."""

from hybrid_search.ingestion.html_parser import EdgarHtmlParser


def test_parse_html_basic():
    sample_html = """
    <html>
        <head>
            <title>NVIDIA 10-K</title>
            <style>body { font-size: 12px; }</style>
            <script>console.log('tracker');</script>
        </head>
        <body>
            <ix:header><ix:hidden>XBRL data</ix:hidden></ix:header>
            <h1>Item 1. Business</h1>
            <p>NVIDIA pioneered <b>GPU-accelerated</b> computing.</p>
            <p>Our revenue grew by &gt; 100% in FY24.&nbsp;Demand remains strong.</p>
        </body>
    </html>
    """
    text = EdgarHtmlParser.parse_html_to_text(sample_html)
    assert "Item 1. Business" in text
    assert "NVIDIA pioneered GPU-accelerated computing." in text
    assert "Our revenue grew by > 100% in FY24. Demand remains strong." in text
    assert "console.log" not in text
    assert "XBRL data" not in text
    assert "style" not in text


def test_parse_html_table_row_to_text():
    sample_table_html = """
    <html>
        <body>
            <p>(in millions, except per share amounts)</p>
            <table>
                <tr>
                    <th>Year Ended</th>
                    <th>2024</th>
                    <th>2023</th>
                    <th>2022</th>
                </tr>
                <tr>
                    <td>Services net sales</td>
                    <td>96,169</td>
                    <td>85,200</td>
                    <td>78,129</td>
                </tr>
                <tr>
                    <td>Diluted earnings per share</td>
                    <td>$6.08</td>
                    <td>$6.13</td>
                    <td>$6.11</td>
                </tr>
                <tr>
                    <td>Weighted-average diluted shares</td>
                    <td>15,408</td>
                    <td>15,672</td>
                    <td>16,215</td>
                </tr>
            </table>
        </body>
    </html>
    """
    text = EdgarHtmlParser.parse_html_to_text(sample_table_html)
    assert "Services net sales: 2024 = 96,169; 2023 = 85,200; 2022 = 78,129. Unit: millions of USD." in text
    assert "Diluted earnings per share: 2024 = $6.08; 2023 = $6.13; 2022 = $6.11. Unit: USD per share." in text
    assert "Weighted-average diluted shares: 2024 = 15,408; 2023 = 15,672; 2022 = 16,215. Unit: millions of shares." in text


def test_parse_html_non_year_table_note4():
    sample_note4_html = """
    <html>
        <body>
            <p>Note 4 – Financial Instruments (in millions)</p>
            <table>
                <tr>
                    <td colspan="4">June 28, 2025</td>
                </tr>
                <tr>
                    <td>&nbsp;</td>
                    <td>AdjustedCost</td>
                    <td>UnrealizedGains</td>
                    <td>FairValue</td>
                </tr>
                <tr>
                    <td>Cash</td>
                    <td>$</td>
                    <td>26,686</td>
                    <td>$</td>
                    <td>—</td>
                    <td>$</td>
                    <td>26,686</td>
                </tr>
                <tr>
                    <td>Money market funds</td>
                    <td>3,779</td>
                    <td>—</td>
                    <td>3,779</td>
                </tr>
            </table>
        </body>
    </html>
    """
    text = EdgarHtmlParser.parse_html_to_text(sample_note4_html)
    assert "Cash (June 28, 2025): Adjusted Cost = $26,686; Unrealized Gains = —; Fair Value = $26,686. Unit: millions of USD." in text
    assert "Money market funds (June 28, 2025): Adjusted Cost = 3,779; Unrealized Gains = —; Fair Value = 3,779. Unit: millions of USD." in text
    assert "|" not in text


def test_parser_distant_header_unit_and_fallback():
    # 1. Distant header (like Apple 10-K separated by multiple tags)
    html_apple = """
    <div>
        <p>CONSOLIDATED STATEMENTS OF OPERATIONS</p>
        <p>(In millions, except number of shares and per share amounts)</p>
        <div><span>Spacer</span></div>
        <div><span>Apple Inc. | 2024 Form 10-K</span></div>
        <table>
            <tr><th>Years Ended</th><th>2024</th><th>2023</th></tr>
            <tr><td>Total net sales</td><td>$391,035</td><td>$383,285</td></tr>
            <tr><td>Diluted earnings per share</td><td>$6.08</td><td>$6.13</td></tr>
        </table>
    </div>
    """
    text_apple = EdgarHtmlParser.parse_html_to_text(html_apple)
    assert "Total net sales: 2024 = $391,035; 2023 = $383,285. Unit: millions of USD." in text_apple
    assert "Diluted earnings per share: 2024 = $6.08; 2023 = $6.13. Unit: USD per share." in text_apple

    # 2. Table with no unit indicated anywhere
    html_no_unit = """
    <div>
        <h2>Operational Count</h2>
        <table>
            <tr><th>Metric</th><th>2024</th><th>2023</th></tr>
            <tr><td>Active Users</td><td>100</td><td>80</td></tr>
        </table>
    </div>
    """
    text_no_unit = EdgarHtmlParser.parse_html_to_text(html_no_unit)
    assert "Active Users: 2024 = 100; 2023 = 80. Unit: unknown unit." in text_no_unit


def test_nearest_table_unit_isolation():
    html_consecutive = """
    <div>
        <p>Statement of Operations (In millions)</p>
        <table>
            <tr><th>Years Ended</th><th>2024</th><th>2023</th></tr>
            <tr><td>Total net sales</td><td>$391,035</td><td>$383,285</td></tr>
        </table>
        <p>Other Financial Data (in thousands)</p>
        <table>
            <tr><th>Years Ended</th><th>2024</th><th>2023</th></tr>
            <tr><td>Marketing expense</td><td>500</td><td>450</td></tr>
        </table>
    </div>
    """
    text = EdgarHtmlParser.parse_html_to_text(html_consecutive)
    assert "Total net sales: 2024 = $391,035; 2023 = $383,285. Unit: millions of USD." in text
    assert "Marketing expense: 2024 = 500; 2023 = 450. Unit: thousands of USD." in text
    # Ensure Table 2 was not incorrectly infected with 'millions of USD'
    assert "Marketing expense: 2024 = 500; 2023 = 450. Unit: millions of USD." not in text


def test_table_intro_merging_and_extractor_fact_pinpoint():
    html_intro = """
    <div>
        <p>The following table shows the computation of basic and diluted earnings per share for 2024, 2023 and 2022 (in millions, except per share):</p>
        <table>
            <tr><th>Years Ended</th><th>2024</th><th>2023</th><th>2022</th></tr>
            <tr><td>Diluted earnings per share</td><td>$6.08</td><td>$6.13</td><td>$6.11</td></tr>
        </table>
    </div>
    """
    text = EdgarHtmlParser.parse_html_to_text(html_intro)
    assert "Table context: The following table shows" in text
    assert "Diluted earnings per share: 2024 = $6.08; 2023 = $6.13; 2022 = $6.11. Unit: USD per share." in text

