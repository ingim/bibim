from __future__ import annotations

from dataclasses import dataclass, asdict

from .index import extract_between


@dataclass
class Reference:
    author: str | None = None
    title: str | None = None
    year: str | None = None
    bibtex: str | None = None
    bibtex_condensed: str | None = None
    venue: str | None = None
    url: str | None = None
    num_citations: str | None = None

    @property
    def author_last_names(self) -> list[str]:
        return [a.strip().split()[-1] for a in self.author.split(',')]

    @property
    def author_concise(self):

        res = [
            "".join([n[0].upper() for n in a.split()[:-1]]) + " " + a.split()[-1]
            for a in self.author.split(',')
        ]
        if len(res) > 2:
            res = [res[0], f"+{len(res) - 2}", res[-1]]
        return ", ".join(res)

    def __eq__(self, other):
        if self.title.lower() != other.title.lower():
            return False

        for a1, a2 in zip(self.author_last_names, other.author_last_names):
            if a1.lower() != a2.lower():
                return False

        return True


class ReferencePageTemplate:
    entries: dict[str, (str, str)]
    layout: str

    def __init__(self, entries: dict[str, (str, str)], layout: str):
        self.entries = entries
        self.layout = layout


class ReferencePage:
    path: str
    template: ReferencePageTemplate
    ref: Reference

    def __init__(self, path: str, ref: Reference, template: ReferencePageTemplate):
        self.path = path
        self.ref = ref
        self.template = template

    @staticmethod
    def create(path: str, ref: Reference, template: ReferencePageTemplate) -> ReferencePage:

        page = ReferencePage(path, ref, template)

        res = {}
        for k, v in asdict(ref).items():
            if k in template.entries:
                res[k] = template.entries[k][0] + v + template.entries[k][1]

        contents = template.layout.format_map(res)
        contents += "\n\n" + "```bibtex\n" + ref.bibtex.strip() + "\n```"
        contents += "\n\n" + "```bibtex\n" + ref.bibtex_condensed.strip() + "\n```"

        with open(path, 'w') as f:
            f.write(contents)

        return page

    @staticmethod
    def load(path: str, template: ReferencePageTemplate) -> ReferencePage:

        # Load tables from path
        with open(path, 'r') as f:
            lines = f.readlines()

        bibtext = []

        parsing_bibtex = False
        bibtex_lines = []

        entries = {}

        for line in lines:

            if line.startswith("```bibtex") and not parsing_bibtex:
                parsing_bibtex = True
                bibtex_lines = []
                continue

            if line.startswith("```") and parsing_bibtex:
                parsing_bibtex = False
                bibtext.append(''.join(bibtex_lines).strip())
                continue

            if parsing_bibtex:
                bibtex_lines.append(line)
                continue

            for key, (prefix, suffix) in template.entries.items():
                if key not in entries:
                    value = extract_between(line, prefix, suffix)
                    if value:
                        entries[key] = value
                        break

        if len(bibtext) == 1:
            entries['bibtex'] = bibtext[0]
        elif len(bibtext) > 1:
            entries['bibtex_condensed'] = bibtext[1]
        else:
            print(f"Warning: No bibtex found in {path}")

        ref = Reference(**entries)
        page = ReferencePage(path, ref, template)

        return page

    def update(self, ref: Reference):

        self.ref = ref

        # Load tables from path
        with open(self.path, 'r') as f:
            lines = f.readlines()

        new_lines = []
        saved = {}
        ref_dict = asdict(self.ref)

        parsing_bibtex = False
        bibtex_count = 0

        for line in lines:

            if line.startswith("```bibtex") and not parsing_bibtex:
                parsing_bibtex = True
                new_lines.append(line)
                continue

            if line.startswith("```") and parsing_bibtex:
                parsing_bibtex = False

                if bibtex_count == 0:
                    new_lines.append(self.ref.bibtex.strip() + "\n")
                else:
                    new_lines.append(self.ref.bibtex_condensed.strip() + "\n")
                new_lines.append(line + "\n")
                bibtex_count += 1
                continue

            if parsing_bibtex:
                continue

            updated = False
            for key, (prefix, suffix) in self.template.entries.items():
                if key not in saved:
                    if extract_between(line, prefix, suffix):
                        saved[key] = True
                        new_lines.append(prefix + ref_dict[key] + suffix)
                        updated = True
                        break
            if not updated:
                new_lines.append(line)

        with open(self.path, 'w') as f:
            f.write(''.join(new_lines))
