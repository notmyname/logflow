# pretty-print columns of text


def table_print(lines_to_print, padding=3):
    one_cell = "%*s"
    line_template = []
    column_widths = []
    for line in lines_to_print:
        cell_count = len(line)
        if cell_count == 2 and line[0] is None:
            continue
        while cell_count > len(line_template):
            line_template.append(one_cell)
            column_widths.append(0)
        for i, cell in enumerate(line):
            cell = str(cell)  # just in case it's not a string already
            len_cell = len(cell)
            if i == 0:
                # don't do extra padding if it's the first column
                target_width = len_cell
            else:
                target_width = len_cell + padding
            if target_width > column_widths[i]:
                column_widths[i] = target_width
    out = []
    col_count = len(column_widths)
    line_template = "".join(line_template)
    for line in lines_to_print:
        if len(line) == 2 and line[0] is None:
            out.append(line[1])
            continue
        while col_count > len(line):
            line += ("",)
        params = tuple(
            item for sublist in zip(column_widths, line) for item in sublist
        )
        out_line = line_template % params
        if out_line.replace(" ", "") == "":
            out_line = ""
        out.append(out_line)
    return "\n".join(out)


if __name__ == "__main__":
    test1 = [
        ("Col1", "Col2"),
        ("10000", "1"),
        ("2", "22222", "22"),
        ("333333",),
    ]
    print(table_print(test1))

    print()

    test2 = [
        ("Tritanium", 22778, "106,060.06 ISK"),
        ("Pyerite", 6222, "23,145.84 ISK"),
        ("Mexallon", 2222, "131,011.90 ISK"),
        ("Isogen", 356, "6,108.07 ISK"),
        ("Nocxium", 133, "39,779.47 ISK"),
        ("Zydrine", 34, "19,601.17 ISK"),
        ("Megacyte", 2, "1,136.51 ISK"),
    ]
    print(table_print(test2, padding=5))
