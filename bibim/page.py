from __future__ import annotations

from .index import extract_between


class PageTemplate:
    entries: dict[str, (str, str)]
    layout: str

    def __init__(self, entries: dict[str, (str, str)], layout: str):
        self.entries = entries
        self.layout = layout


class Page:
    path: str
    template: PageTemplate
    data: dict[str, str]

    def __init__(self, path: str, template: PageTemplate):
        self.path = path
        self.template = template
        self.data = {}

    @staticmethod
    def create(data: dict[str, str], path: str, template: PageTemplate) -> Page:

        page = Page(path, template)
        page.data = data

        contents = template.layout.format_map(page.data)

        with open(path, 'w') as f:
            f.write(contents)

        return page

    @staticmethod
    def load(path: str, template: PageTemplate) -> Page:

        paper = Page(path, template)

        # Load tables from path
        with open(path, 'r') as f:
            lines = f.readlines()

        for line in lines:
            for key, (prefix, suffix) in template.entries.items():
                if key not in paper.data:
                    value = extract_between(line, prefix, suffix)
                    if value:
                        paper.data[key] = value
                        break

        return paper

    def save(self):

        # Load tables from path
        with open(self.path, 'r') as f:
            lines = f.readlines()

        new_lines = []
        saved = {}

        for line in lines:
            updated = False
            for key, (prefix, suffix) in self.template.entries.items():
                if key not in saved:
                    if extract_between(line, prefix, suffix):
                        saved[key] = True
                        new_lines.append(prefix + self.data[key] + suffix)
                        updated = True
                        break
            if not updated:
                new_lines.append(line)

        with open(self.path, 'w') as f:
            f.writelines(new_lines)
