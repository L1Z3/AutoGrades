# TODO Figure out how GPA works
# TODO Make graphs
# TODO Implement assignments & maybe assignments -> % calculation
# TODO Maybe even get assignment averages, high, low, etc?


import gspread
from oauth2client.service_account import ServiceAccountCredentials
from time import time
from time import sleep
from canvasapi import Canvas
import pickle
import os
from sys import exit

API_URL = "https://stxavier.instructure.com/api/v1/"
API_KEY = "key was out of date (changed key, also, in preparation of going public on repo)"


def save(data, path):
    with open(path, 'wb') as handle:
        pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)


def load(path):
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            return pickle.load(f)
    else:
        open(path, 'a').close()
        return None


def calc_letter(percent):
    if isinstance(percent, str):
        percent_num = float(percent.replace("%", ""))
    elif isinstance(percent, int):
        percent_num = float(percent)
    elif isinstance(percent, float):
        percent_num = percent
    else:
        print("Invalid type in percent.")
        return
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
    else:
        print("This should never happen.")
        return "WAT"


def calc_gpa(percent):
    # TODO Make this
    return


def authorize_client():
    scope = ["https://spreadsheets.google.com/feeds"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("client_secret.json", scope)
    client = gspread.authorize(creds)
    return client


def get_grades():
    canvas = Canvas(API_URL, API_KEY)
    # print(canvas.get_user(6893).get_enrollments()[0])
    # for course in canvas.get_courses():
    #     print(list(course.get_users()))
    courses_unordered = []
    for course in list(canvas.get_courses(include="total_scores")):
        score = course.enrollments[0].get('computed_current_score')
        if score is None:
            continue
        name = course.name
        if name == "Bombers 2021":
            continue
        courses_unordered.append([name, score])
    courses = [[], [], [], [], [], [], []]
    for course in courses_unordered:
        if course[0] == "Scriptures":
            courses[0] = course
        elif course[0] == "AP World":
            courses[1] = course
        elif course[0] == "Strings":
            courses[2] = course
        elif course[0] == "English":
            courses[3] = course
        elif course[0] == "Spanish":
            courses[4] = course
        elif course[0] == "Biology":
            courses[5] = course
        elif course[0] == "Algebra":
            courses[6] = course
    return [canvas, courses]


def get_assignments(canvas):
    names = ["Scriptures", "AP World", "Strings", "English", "Spanish", "Biology", "Algebra"]
    assignments = []
    for course in list(canvas.get_courses()):
        name = course.name
        if name not in names:
            continue
        course_assignments = []
        for assignment in course.get_assignments(include="submission"):
            assignment_name = assignment.name
            assignment_score = assignment.submission.get('score')
            assignment_points_possible = assignment.points_possible
            if assignment_score is None:
                continue
            course_assignments.append([assignment_name, assignment_score, assignment_points_possible])
        assignments.append([name, course_assignments])
    return assignments


while True:
    # course_weight = [0.5, 1.0, 0, 0.5, 0, 0.5, 0.5]

    data = get_grades()
    courses = data[1]
    canvas = data[0]
    # temp_data = [[u'Scriptures', u'97.16%'], [u'Algebra', u'98.08%'], [u'AP World', u'96.06%'], [u'Biology', u'99.04%'], [u'Strings', u'97.4%'], [u'English', u'94.51%'], [u'Spanish', u'100.61%']]
    print("Updating to spreadsheet...")
    client = authorize_client()
    sheet = client.open("Semester 1 Auto Grade").worksheet("Overview")

    row = sheet.col_values(1).index("") + 1
    prev_values = []
    for value in sheet.row_values(row - 1):
        if "%" in value:
            value = float(value.replace("%", ""))
        else:
            continue
        prev_values.append(value)
    prev_values.pop()
    prev_prev_values = []
    for value in sheet.row_values(row - 2):
        if "%" in value:
            value = float(value.replace("%", ""))
        else:
            continue
        prev_prev_values.append(value)
    prev_prev_values.pop()
    temp_list = []
    for course in courses:
        temp_list.append(course[1])
    if prev_prev_values == prev_values == temp_list:
        sheet.update_cell(row - 1, 1, time())
        print("No change in grades. Waiting for one hour.")
        sleep(3600)
        continue

    assignments = get_assignments(canvas)
    column = 2
    sheet.update_cell(row, column, "=(A" + str(row) + "-14400)/86400+date(1970,1,1)")
    column += 1
    temp_time = time()
    for course in courses:
        for c in assignments:
            if course[0] == c[0]:
                course_num = assignments.index(c)

        sheet.update_cell(row, column, float(course[1]) / 100)
        column += 1
        sheet.update_cell(row, column, calc_letter(course[1]))
        column += 1
        # TODO make GPA work
        column += 1
        course_sheet = client.open("Semester 1 Auto Grade").worksheet(course[0])
        assignment_column = 3
        start = course_sheet.col_values(3).index("") + 1
        # print(start)
        cur = start
        course_sheet.update_cell(cur, assignment_column, "assignment_names")
        cur += 1
        course_sheet.update_cell(cur, assignment_column, "assignment_num")
        cur += 1
        course_sheet.update_cell(cur, assignment_column, "assignment_den")
        cur += 1
        course_sheet.update_cell(cur, assignment_column, "assignment_percent")
        cur += 1
        course_sheet.update_cell(cur, assignment_column, "assignment_letter")
        assignment_column += 1
        # TODO fix order for assignments
        for assignment in assignments[course_num][1]:
            for i in range(start, start + 5):
                if i == start:
                    while True:
                        try:
                            course_sheet.update_cell(i, assignment_column, assignment[0])
                        except TypeError:
                            course_sheet.add_cols(10)
                            continue
                        break
                elif i == start + 1:
                    course_sheet.update_cell(i, assignment_column, assignment[1])
                elif i == start + 2:
                    course_sheet.update_cell(i, assignment_column, assignment[2])
                elif i == start + 3:
                    try:
                        course_sheet.update_cell(i, assignment_column, assignment[1] / assignment[2])
                    except ZeroDivisionError:
                        course_sheet.update_cell(i, assignment_column, "N/A")
                elif i == start + 4:
                    try:
                        course_sheet.update_cell(i, assignment_column, calc_letter(assignment[1] / assignment[2] * 100))
                    except ZeroDivisionError:
                        course_sheet.update_cell(i, assignment_column, "N/A")
            assignment_column += 1
        course_sheet.update_cell(start, 1, temp_time)
        course_sheet.update_cell(start, 2, "=(A" + str(start) + "-14400)/86400+date(1970,1,1)")

    sheet.update_cell(row, column,
                      "=AVERAGE(C" + str(row) + ",F" + str(row) + ",I" + str(row) + ",L" + str(row) + ",O" + str(
                          row) + ",R" + str(row) + ",U" + str(row) + ")")
    avg_temp = sheet.cell(row, column).value
    column += 1
    sheet.update_cell(row, column, calc_letter(avg_temp))
    column += 1
    # TODO
    sheet.update_cell(row, 1, temp_time)
    print("Waiting for one hour.")
    sleep(3600)
# TODO add console output on progress
# TODO add cell saying progress is happening on overview page
# TODO fix random request errors?
