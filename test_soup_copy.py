
from bs4 import BeautifulSoup
import copy

html = "<html><body><nav>Menu</nav><main>Content</main></body></html>"
soup = BeautifulSoup(html, 'html.parser')
print(f"Original before: {soup}")

# Simulation of html_to_markdown behavior
content = copy.copy(soup)
for tag in content.find_all('nav'):
    tag.decompose()

print(f"Copy after decompose: {content}")
print(f"Original after decompose: {soup}")
