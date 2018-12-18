def round_traditional(val, digits):
    """
    A rounding function that fixes some precision errors when rounding grades

    :param val: Value to round
    :param digits: Number of digits to round to
    :return: Rounded value
    """
    # black magic to fix rounding
    return round(val + 10 ** (-len(str(val)) - 1), digits)


def calc_letter(percent):
    """
    Calculates letter grade for given percent

    :param percent: Percent to calculate for
    :return: Letter grade as String
    """
    # if it's a string, replace the percent and convert it to a float
    if isinstance(percent, str):
        percent_num = float(percent.replace("%", ""))
    # if it's an int, convert it to a float
    elif isinstance(percent, int):
        percent_num = float(percent)
    # if it's a float, just keep that
    elif isinstance(percent, float):
        percent_num = percent
    else:
        print("Invalid type in percent.")
        return
    # Just return hard-coded letter grade for each percent.
    # These come straight from the handbook.

    # Now that I think about it, I should probably round before I calculate
    # the letter grade, or maybe I had a reason for not doing so when writing
    # this method (which I don't use in the current iteration of the program.)
    # TODO figure this out
    if percent_num >= 97:
        return "A+"
    elif percent_num >= 93:
        return "A"
    elif percent_num >= 90:
        return "A-"
    elif percent_num >= 86:
        return "B+"
    elif percent_num >= 83:
        return "B"
    elif percent_num >= 80:
        return "B-"
    elif percent_num >= 78:
        return "C+"
    elif percent_num >= 75:
        return "C"
    elif percent_num >= 73:
        return "D+"
    elif percent_num >= 70:
        return "D"
    elif percent_num < 70:
        return "F"


def calc_gpa_for_percent(percent, weight):
    """
    Given a percent and weight for a class, calculate the GPA of that specific class

    :param percent: Percent grade to calculate
    :param weight: Weight to calculate GPA
    :return: GPA for that specific class as a float
    """
    # this if/elif block converts input to an int and rounds
    if isinstance(percent, str):
        percent_num = int(round_traditional(float(percent.replace("%", "")), 0))
    elif isinstance(percent, float):
        percent_num = int(round_traditional(float(percent), 0))
    elif isinstance(percent, int):
        percent_num = percent
    else:
        print("Invalid type in percent.")
        return

    # If it's greater than 97 after being rounded, use 4.33 plus the weight
    if percent_num >= 97:
        return round_traditional(4.33 + weight, 2)
    # use hard-coded GPA values for each percent (I reverse engineered these--the specific values
    # aren't available in the handbook)
    elif percent_num >= 70:
        unweighted_gpas = {70: 1.0, 71: 1.2, 72: 1.4, 73: 1.6, 74: 1.8, 75: 2.0, 76: 2.11, 77: 2.22, 78: 2.33,
                           79: 2.5, 80: 2.67, 81: 2.78, 82: 2.89, 83: 3.0, 84: 3.11, 85: 3.22, 86: 3.33, 87: 3.41,
                           88: 3.49, 89: 3.58, 90: 3.67, 91: 3.78, 92: 3.89, 93: 4.0, 94: 4.08, 95: 4.16, 96: 4.25}
        return round_traditional(unweighted_gpas[percent_num] + weight, 2)
    else:
        return round_traditional(weight, 2)


def calc_total_gpa(courses, scores):
    """
    Calculates overall GPA given a list of courses and scores

    :param courses: Course data as made in get_grades()
    :param scores: Score data as made in get_grades()
    :return: Final GPA as a float
    """
    gpas = []
    # iterate through courses in course data
    for course in courses:
        # Add the current GPA to the list, which is retrieved from
        # calc_gpa_for_percent based on the current score and course
        gpas.append(calc_gpa_for_percent(scores[course], courses[course]["weight"]))
    if len(gpas) == 0:
        print("Couldn't get any GPAs. This means that something is broken.")
        exit(1)
    # average all the GPAs for each individual course and round to two decimal places
    final_gpa = round_traditional(sum(gpas) / float(len(gpas)), 2)
    return final_gpa


def hex_to_rgb(hexa):
    """
    Converts a hexadecimal color string to an RGB value

    :param hexa: String for hex color in format "FFFFFF" or "FFF"
    :return: list contain red, green, and blue values in decimal
    """
    # convert string to list of characters
    hexa = list(hexa)
    # TIL that there's a shorthand for hex colors with 3 digits
    # This accounts for that case
    if len(hexa) == 3:
        hexa.insert(0, hexa[0])
        hexa.insert(2, hexa[2])
        hexa.insert(4, hexa[4])
    # lists storing indiviual characters corresponding to each color
    redl = []
    greenl = []
    bluel = []
    # first two hexadecimal digits go to red
    redl.append(hexa[0])
    redl.append(hexa[1])
    # second two hexadecimal digits go to green
    greenl.append(hexa[2])
    greenl.append(hexa[3])
    # third two hexadecimal digits go to blue
    bluel.append(hexa[4])
    bluel.append(hexa[5])
    # convert each two element list to a string
    red = "".join(redl)
    blue = "".join(bluel)
    green = "".join(greenl)
    # convert each string from hexadecimal to decimal and return a list with values for all three colors
    return [int(red, 16), int(green, 16), int(blue, 16)]
