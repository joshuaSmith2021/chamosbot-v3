# These functions are written by jadenPete and I, I just
# stole them to make my work a bit easier in this repo

class Matrix(list):
    def __init__(self, width, height, fill=" "):
        self.extend([fill] * width for _ in range(height))

    def __str__(self):
        return "\n".join(map("".join, self))


class Table(list):
    def __init__(self, iterable=[], just="left", sep=" "):
        self.extend(iterable)

        self.just = just
        self.sep = sep

    def str_len(self, string):
        return len(str(string))

    def __str__(self):
        # Find the maximum of each column by rotating the two-dimensional array
        widths = [max(map(self.str_len, row)) for row in zip(*self)]
        result = []

        for row in self:
            if self.just == "left":
                result.append(self.sep.join(str(value).ljust(widths[i]) for i, value in enumerate(row)))
            else:
                result.append(self.sep.join(str(value).rjust(widths[i]) for i, value in enumerate(row)))

        return "\n".join(result)
