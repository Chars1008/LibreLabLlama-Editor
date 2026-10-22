import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\Chars Hsieh\Desktop\Editor project')
from LibreLlamaLabEditor import AcademicReviewerApp, AcademicReviewReport, IssueItem, RevisionOption
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)
win = AcademicReviewerApp()

draft = '''Our preliminary experiments definitely prove that our new neural architecture completely solves the latency bottleneck in cloud networks. A lot of users were extremely happy because it runs very fast. Therefore, this framework will undeniably replace all classical networking algorithms within two years.

Moreover, we observed a direct correlation between memory consumption and CPU temperature, which undeniably causes severe catastrophic server failures without any other factors. We made an experiment to verify this.'''

win.text_editor.setPlainText(draft)

issues = [
    IssueItem(
        category='Collocation Defect', original_text='definitely prove',
        revision_options=[RevisionOption(style_label='A', revised_text='demonstrate'), RevisionOption(style_label='B', revised_text='indicate')]
    ),
    IssueItem(
        category='Collocation Defect', original_text='completely solves',
        revision_options=[RevisionOption(style_label='A', revised_text='substantially addresses'), RevisionOption(style_label='B', revised_text='effectively resolves')]
    ),
    IssueItem(
        category='Grammar & Mechanics', original_text='definitely prove that our new neural architecture completely solves...',
        revision_options=[RevisionOption(style_label='A', revised_text='Our preliminary results suggest that the proposed neural architecture significantly mitigates...'), RevisionOption(style_label='B', revised_text='The experimental data indicate that our architecture effectively addresses...')]
    ),
    IssueItem(
        category='Collocation Defect', original_text='made an experiment',
        revision_options=[RevisionOption(style_label='A', revised_text='conducted an experiment'), RevisionOption(style_label='B', revised_text='performed an experiment')]
    ),
]

report = AcademicReviewReport(
    article_gist_zh='test', overall_assessment_zh='test',
    issues=issues, research_recommendations=[]
)
win.on_review_finished(report)

cards = []
for i in range(win.discourse_layout.count()):
    w = win.discourse_layout.itemAt(i).widget()
    if w and hasattr(w, 'option_buttons'):
        cards.append(w)

for i in range(win.colloc_layout.count()):
    w = win.colloc_layout.itemAt(i).widget()
    if w and hasattr(w, 'option_buttons'):
        cards.append(w)

print(f'Total cards found: {len(cards)}')
for idx, card in enumerate(cards):
    print(f'Card {idx}: issue_idx={card.issue_idx}, orig="{card.issue.original_text[:20]}", btn_count={len(card.option_buttons)}')

print('\n--- Clicking Card 0 Option 1 ---')
t_before = win.latest_revised_plain_text
cards[0].option_buttons[1].click()
t_after1 = win.latest_revised_plain_text
print(f'Card 0 btn 1 text: {cards[0].option_buttons[1].text()}')
print(f'Text changed? {t_before != t_after1}')

print('\n--- Clicking Card 1 Option 1 ---')
cards[1].option_buttons[1].click()
t_after2 = win.latest_revised_plain_text
print(f'Card 1 btn 1 text: {cards[1].option_buttons[1].text()}')
print(f'Text changed? {t_after1 != t_after2}')

print('\n--- Clicking Card 2 Option 1 ---')
cards[2].option_buttons[1].click()
t_after3 = win.latest_revised_plain_text
print(f'Card 2 btn 1 text: {cards[2].option_buttons[1].text()}')
print(f'Text changed? {t_after2 != t_after3}')
