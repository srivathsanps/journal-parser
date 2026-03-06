"""
PDF Report Generator for Revit Journal Analyzer
Generates professional PDF reports with charts, timelines, and issue summaries.
"""

import io
from datetime import datetime
from typing import Dict, Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend


class PDFReportGenerator:
    """Generate PDF reports from parsed journal data."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='Title2',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1a1a2e')
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#16213e')
        ))

        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading3'],
            fontSize=11,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#0f3460')
        ))

        self.styles.add(ParagraphStyle(
            name='BodySmall',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=6
        ))

        self.styles.add(ParagraphStyle(
            name='IssueText',
            parent=self.styles['Normal'],
            fontSize=8,
            leftIndent=20,
            textColor=colors.HexColor('#333333')
        ))

        self.styles.add(ParagraphStyle(
            name='CriticalText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#dc3545'),
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='WarningText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#ffc107')
        ))

    def generate(self) -> bytes:
        """Generate PDF report and return as bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        story = []

        # Title and header
        story.extend(self._build_header())

        # Summary section with charts
        story.extend(self._build_summary_section())

        # Session information
        story.extend(self._build_session_section())

        # Issues and errors
        story.extend(self._build_issues_section())

        # Timeline
        story.extend(self._build_timeline_section())

        # Add-ins
        story.extend(self._build_addins_section())

        # Workflow events
        story.extend(self._build_workflow_section())

        # Known issues with KB links
        story.extend(self._build_kb_section())

        # Build the PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _build_header(self) -> List:
        """Build report header."""
        elements = []

        # Title
        elements.append(Paragraph("Revit Journal Analysis Report", self.styles['Title2']))

        # Generation info
        gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elements.append(Paragraph(f"Generated: {gen_time}", self.styles['BodySmall']))

        session = self.data.get('session_info', {})
        if session.get('journal_file'):
            elements.append(Paragraph(f"Journal: {session['journal_file']}", self.styles['BodySmall']))

        elements.append(Spacer(1, 20))

        # Session status banner
        session_status = self.data.get('summary', {}).get('session_status', 'Unknown')
        if session_status == 'Crashed':
            status_table = Table(
                [[Paragraph("CRASHED", self.styles['CriticalText'])]],
                colWidths=[500]
            )
            status_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff3f3')),
                ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#dc3545')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(status_table)
            elements.append(Spacer(1, 15))
        elif session_status == 'Active/Terminated':
            status_table = Table(
                [[Paragraph("ACTIVE / TERMINATED", self.styles['WarningText'] if hasattr(self.styles, 'WarningText') else self.styles['BodySmall'])]],
                colWidths=[500]
            )
            status_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff8e1')),
                ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#ffc107')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(status_table)
            elements.append(Spacer(1, 15))

        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0')))
        elements.append(Spacer(1, 15))

        return elements

    def _build_summary_section(self) -> List:
        """Build summary section with charts."""
        elements = []
        summary = self.data.get('summary', {})

        elements.append(Paragraph("Executive Summary", self.styles['SectionHeader']))

        # Summary stats table
        stats_data = [
            ['Metric', 'Value'],
            ['Total Errors', str(summary.get('total_errors', 0))],
            ['Total Warnings', str(summary.get('total_warnings', 0))],
            ['Known Issues Found', str(summary.get('known_issues_found', 0))],
            ['Critical Issues', str(summary.get('critical_issues', 0))],
            ['High Priority Issues', str(summary.get('high_issues', 0))],
            ['Models Opened', str(summary.get('models_count', 0))],
            ['Sync Operations', str(summary.get('sync_operations', 0))],
            ['Add-ins Loaded', str(summary.get('addins_count', 0))],
            ['Failed Add-ins', str(summary.get('failed_addins', 0))],
        ]

        stats_table = Table(stats_data, colWidths=[200, 100])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 20))

        # Issues severity chart
        chart = self._create_severity_chart(summary)
        if chart:
            elements.append(chart)
            elements.append(Spacer(1, 15))

        return elements

    def _create_severity_chart(self, summary: Dict) -> Drawing:
        """Create a severity distribution pie chart."""
        critical = summary.get('critical_issues', 0)
        high = summary.get('high_issues', 0)
        medium = summary.get('medium_issues', 0)
        low = summary.get('known_issues_found', 0) - critical - high - medium

        if critical + high + medium + low == 0:
            return None

        drawing = Drawing(400, 150)

        # Pie chart
        pie = Pie()
        pie.x = 100
        pie.y = 20
        pie.width = 100
        pie.height = 100
        pie.data = [critical, high, medium, max(0, low)]
        pie.labels = ['Critical', 'High', 'Medium', 'Low/Info']
        pie.slices.strokeWidth = 0.5

        pie.slices[0].fillColor = colors.HexColor('#dc3545')
        pie.slices[1].fillColor = colors.HexColor('#fd7e14')
        pie.slices[2].fillColor = colors.HexColor('#ffc107')
        pie.slices[3].fillColor = colors.HexColor('#28a745')

        drawing.add(pie)

        # Legend
        legend = Legend()
        legend.x = 250
        legend.y = 80
        legend.alignment = 'right'
        legend.columnMaximum = 4
        legend.colorNamePairs = [
            (colors.HexColor('#dc3545'), f'Critical ({critical})'),
            (colors.HexColor('#fd7e14'), f'High ({high})'),
            (colors.HexColor('#ffc107'), f'Medium ({medium})'),
            (colors.HexColor('#28a745'), f'Low/Info ({max(0, low)})'),
        ]
        drawing.add(legend)

        # Title
        drawing.add(String(200, 135, "Issue Severity Distribution",
                           fontSize=10, textAnchor='middle'))

        return drawing

    def _build_session_section(self) -> List:
        """Build session information section."""
        elements = []
        session = self.data.get('session_info', {})

        elements.append(Paragraph("Session Information", self.styles['SectionHeader']))

        session_data = [
            ['Property', 'Value'],
            ['Revit Version', session.get('revit_version', 'N/A')],
            ['Build Number', session.get('build_number', 'N/A')],
            ['Computer', session.get('computer_name', 'N/A')],
            ['Username', session.get('username', 'N/A')],
            ['Operating System', session.get('operating_system', 'N/A')],
            ['RAM', session.get('ram', 'N/A')],
            ['Graphics Card', session.get('graphics_card', 'N/A')],
            ['Session Start', session.get('session_start', 'N/A')],
            ['Session End', session.get('session_end', 'N/A')],
            ['Session Duration', session.get('session_duration', 'N/A')],
            ['Session Status', session.get('session_status', 'Unknown')],
        ]

        session_table = Table(session_data, colWidths=[150, 340])
        session_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(session_table)
        elements.append(Spacer(1, 10))

        # Models opened
        if session.get('models_opened'):
            elements.append(Paragraph("Models Opened:", self.styles['SubHeader']))
            for model in session['models_opened'][:10]:  # Limit to 10
                elements.append(Paragraph(f"  {model}", self.styles['BodySmall']))

        elements.append(Spacer(1, 15))
        return elements

    def _build_issues_section(self) -> List:
        """Build errors and issues section."""
        elements = []
        errors = self.data.get('errors', {})

        elements.append(Paragraph("Errors and Warnings", self.styles['SectionHeader']))

        # Fatal errors
        fatal = errors.get('fatal', [])
        if fatal:
            elements.append(Paragraph(f"Fatal Errors ({len(fatal)})", self.styles['SubHeader']))
            for err in fatal[:15]:  # Limit
                text = self._truncate_text(err.get('text', ''), 120)
                elements.append(Paragraph(
                    f"Line {err.get('line', '?')}: {text}",
                    self.styles['CriticalText']
                ))
            elements.append(Spacer(1, 10))

        # Errors
        errs = errors.get('errors', [])
        if errs:
            elements.append(Paragraph(f"Errors ({len(errs)})", self.styles['SubHeader']))
            for err in errs[:20]:  # Limit
                text = self._truncate_text(err.get('text', ''), 120)
                elements.append(Paragraph(
                    f"Line {err.get('line', '?')}: {text}",
                    self.styles['IssueText']
                ))
            if len(errs) > 20:
                elements.append(Paragraph(f"... and {len(errs) - 20} more errors", self.styles['BodySmall']))
            elements.append(Spacer(1, 10))

        # Warnings
        warnings = errors.get('warnings', [])
        if warnings:
            elements.append(Paragraph(f"Warnings ({len(warnings)})", self.styles['SubHeader']))
            for warn in warnings[:15]:  # Limit
                text = self._truncate_text(warn.get('text', ''), 120)
                elements.append(Paragraph(
                    f"Line {warn.get('line', '?')}: {text}",
                    self.styles['IssueText']
                ))
            if len(warnings) > 15:
                elements.append(Paragraph(f"... and {len(warnings) - 15} more warnings", self.styles['BodySmall']))

        elements.append(Spacer(1, 15))
        return elements

    def _build_timeline_section(self) -> List:
        """Build timeline section."""
        elements = []
        timeline = self.data.get('timeline', [])

        if not timeline:
            return elements

        elements.append(Paragraph("Session Timeline", self.styles['SectionHeader']))

        # Build timeline table
        timeline_data = [['Line', 'Event', 'Details']]
        for event in timeline[:30]:  # Limit
            event_type = event.get('type', '')
            desc = event.get('description', '')
            text = self._truncate_text(event.get('text', ''), 80)

            # Color code by event type
            if event_type in ['crash', 'error']:
                desc = f'<font color="#dc3545">{desc}</font>'

            timeline_data.append([
                str(event.get('line', '')),
                Paragraph(desc, self.styles['BodySmall']),
                Paragraph(text, self.styles['BodySmall'])
            ])

        timeline_table = Table(timeline_data, colWidths=[50, 120, 320])
        timeline_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(timeline_table)
        elements.append(Spacer(1, 15))

        return elements

    def _build_addins_section(self) -> List:
        """Build add-ins section."""
        elements = []
        addins = self.data.get('addins', {})

        autodesk = addins.get('autodesk', [])
        third_party = addins.get('third_party', [])
        failed = addins.get('failed', [])

        if not (autodesk or third_party or failed):
            return elements

        elements.append(Paragraph("Add-ins", self.styles['SectionHeader']))

        # Failed add-ins (show first)
        if failed:
            elements.append(Paragraph(f"Failed Add-ins ({len(failed)})", self.styles['SubHeader']))
            for addin in failed[:10]:
                elements.append(Paragraph(
                    f"Line {addin.get('line', '?')}: {addin.get('name', 'Unknown')}",
                    self.styles['CriticalText']
                ))
            elements.append(Spacer(1, 10))

        # Third-party
        if third_party:
            elements.append(Paragraph(f"Third-Party Add-ins ({len(third_party)})", self.styles['SubHeader']))
            for addin in third_party[:15]:
                elements.append(Paragraph(
                    f"  {addin.get('name', 'Unknown')}",
                    self.styles['BodySmall']
                ))
            elements.append(Spacer(1, 10))

        # Autodesk
        if autodesk:
            elements.append(Paragraph(f"Autodesk Add-ins ({len(autodesk)})", self.styles['SubHeader']))
            for addin in autodesk[:10]:
                elements.append(Paragraph(
                    f"  {addin.get('name', 'Unknown')}",
                    self.styles['BodySmall']
                ))

        elements.append(Spacer(1, 15))
        return elements

    def _build_workflow_section(self) -> List:
        """Build workflow events section."""
        elements = []
        workflow = self.data.get('workflow', {})

        sync_ops = workflow.get('sync_operations', [])
        file_ops = workflow.get('file_operations', [])
        link_ops = workflow.get('link_operations', [])

        if not (sync_ops or file_ops or link_ops):
            return elements

        elements.append(Paragraph("Workflow Events", self.styles['SectionHeader']))

        if sync_ops:
            elements.append(Paragraph(f"Sync Operations ({len(sync_ops)})", self.styles['SubHeader']))
            for op in sync_ops[:10]:
                text = self._truncate_text(op.get('text', ''), 100)
                elements.append(Paragraph(f"Line {op.get('line', '?')}: {text}", self.styles['BodySmall']))
            elements.append(Spacer(1, 10))

        if link_ops:
            elements.append(Paragraph(f"Link Operations ({len(link_ops)})", self.styles['SubHeader']))
            for op in link_ops[:10]:
                text = self._truncate_text(op.get('text', ''), 100)
                elements.append(Paragraph(f"Line {op.get('line', '?')}: {text}", self.styles['BodySmall']))

        elements.append(Spacer(1, 15))
        return elements

    def _build_kb_section(self) -> List:
        """Build knowledge base articles section."""
        elements = []
        matched = self.data.get('kb_articles', [])

        # Filter to only those with KB links
        kb_issues = [m for m in matched if m.get('kb_article')]

        if not kb_issues:
            return elements

        elements.append(PageBreak())
        elements.append(Paragraph("Autodesk Knowledge Base Articles", self.styles['SectionHeader']))
        elements.append(Paragraph(
            "The following known issues were detected in the journal file. "
            "Click the links for official Autodesk solutions.",
            self.styles['BodySmall']
        ))
        elements.append(Spacer(1, 10))

        for issue in kb_issues[:25]:  # Limit
            severity = issue.get('severity', 'info')
            severity_color = {
                'critical': '#dc3545',
                'high': '#fd7e14',
                'medium': '#ffc107',
                'low': '#28a745',
                'info': '#17a2b8'
            }.get(severity, '#6c757d')

            # Issue header
            elements.append(Paragraph(
                f'<font color="{severity_color}"><b>[{severity.upper()}]</b></font> Line {issue.get("line", "?")}',
                self.styles['BodySmall']
            ))

            # Pattern matched
            pattern = self._truncate_text(issue.get('pattern', ''), 80)
            elements.append(Paragraph(f"Pattern: {pattern}", self.styles['IssueText']))

            # KB link
            kb_url = issue.get('kb_article', '')
            if kb_url:
                elements.append(Paragraph(
                    f'<link href="{kb_url}"><font color="blue"><u>{kb_url}</u></font></link>',
                    self.styles['IssueText']
                ))

            elements.append(Spacer(1, 8))

        return elements

    def _truncate_text(self, text: str, max_len: int) -> str:
        """Truncate text and escape special characters."""
        # Remove problematic characters
        text = text.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
        if len(text) > max_len:
            return text[:max_len] + '...'
        return text


def generate_pdf(data: Dict[str, Any]) -> bytes:
    """Convenience function to generate PDF from parsed data."""
    generator = PDFReportGenerator(data)
    return generator.generate()
