from sys import exit
import os
import pickle
import multiprocessing
import datetime
from time import time, gmtime, strftime, localtime
from time import sleep, daylight
from requests.exceptions import ConnectionError
from json.decoder import JSONDecodeError
import configparser

from canvasapi import Canvas
import plotly.graph_objs as go
import plotly.offline as offline


parser = configparser.RawConfigParser()
parser.read(r"config.txt")
student_name = parser.get("AutoGrades_Config", "student_name")
output = parser.get("AutoGrades_Config", "line_path")
output_gpa = parser.get("AutoGrades_Config", "gpa_line_path")
time_offset = int(parser.get("AutoGrades_Config", "time_offset"))
API_URL = "https://stxavier.instructure.com/"
API_KEY = parser.get("AutoGrades_Config", "api_key")


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


def round_traditional(val, digits):  # this function fixes problems with precision errors in rounding
   return round(val+10**(-len(str(val))-1), digits)


def calc_letter(percent):  # this calculates the letter grade given a certain percent
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


def calc_gpa_for_percent(percent, weight):
    if isinstance(percent, str):
        percent_num = int(round_traditional(float(percent.replace("%", "")), 0))
    elif isinstance(percent, float):
        percent_num = int(round_traditional(float(percent), 0))
    elif isinstance(percent, int):
        percent_num = percent
    else:
        print("Invalid type in percent.")
        return
    if percent_num >= 97:
        return round_traditional(4.33 + weight, 2)
    elif percent_num >= 70:
        unweighted_gpas = {70: 1.0, 71: 1.2, 72: 1.4, 73: 1.6, 74: 1.8, 75: 2.0, 76: 2.11, 77: 2.22, 78: 2.33, 79: 2.5, 80: 2.67, 81: 2.78, 82: 2.89, 83: 3.0, 84: 3.11, 85: 3.22, 86: 3.33, 87: 3.41, 88: 3.49, 89: 3.58, 90: 3.67, 91: 3.78, 92: 3.89, 93: 4.0, 94: 4.08, 95: 4.16, 96: 4.25}
        return round_traditional(unweighted_gpas[percent_num] + weight, 2)
    else:
        return round_traditional(weight, 2)


def calc_total_gpa(percents, weights):
    if len(percents) != len(weights):
        print("There are not the same number of percents and weights.")
        print("Fix this.")
        exit(0)
    gpas = []
    i = 0
    for percent in percents:
        gpas.append(calc_gpa_for_percent(percent, weights[i]))
        i += 1
    final_gpa = round_traditional(sum(gpas) / float(len(gpas)), 2)
    return final_gpa


def get_grades(queue):
    canvas = Canvas(API_URL, API_KEY)
    # print(canvas.get_user(6893).get_enrollments()[0])
    # for course in canvas.get_courses():
    #     print(list(course.get_users()))
    # print(canvas.get_current_user().get_colors())
    # exit(0)
    courses = {}
    scores = []
    weights = []
    while True:
        try:
            for course in list(canvas.get_courses(include=["total_scores", "current_grading_period_scores"])):
                score = course.enrollments[0].get('current_period_computed_current_score')  # change to 'current_period_computed_current_score' after 3rd quarter
                # print(course.enrollments[0])
                # exit(0)
                if score is None:
                    continue
                name = course.name
                if name == "Bombers 2021":
                    continue
                if " S2" not in name:  # this is to prevent Semester 1 courses from being included
                    continue
                original_name = course.original_name
                weight = 0
                if "Accelerated" in original_name or "Honors" in original_name:
                    weight = 0.5
                elif "AP" in original_name:
                    weight = 1
                # course_assignments = {}
                # for assignment in course.get_assignments(include="submission"):
                #     assignment_name = assignment.name
                #     assignment_score = assignment.submission.get('score')
                #     assignment_points_possible = assignment.points_possible
                #     if assignment_score is None:
                #         continue
                #     course_assignments[assignment_name] = [assignment_score, assignment_points_possible]
                courses[name] = {'score': score}
                scores.append(score)
                weights.append(weight)
            break
        except ConnectionError:
            print("ConnectionError while getting grades. Trying again.")
            continue
        except JSONDecodeError:
            print("Unexpected JSONDecodeError when getting grades. Trying again.")
            continue
    courses['estimated_gpa'] = calc_total_gpa(scores, weights)
    # print(courses['estimated_gpa'])
    queue.put(courses)


def create_graph(filename):
    colors = {"English S2": "FF0000", "Biology S2": "43A047", "AP World S2": "000000", "Algebra S2": "2083C5", "Scriptures S2": "F06291", "Spanish S2": "F0592B", "OC S2": "A52A2A", "IP S2": "3CA184"}
    files = os.listdir("data")
    x = {}
    y = {}
    skip = False
    for time in files:
        skip = False
        curr = load("data\\" + time)
        for key in curr:
            if str(key) == "estimated_gpa":
                continue
            inttime = int(time.replace(".db", ""))
            subtime = time_offset  # time to subtract
            truetime = datetime.datetime.fromtimestamp(inttime-subtime)  # minus is for timezone difference + daylight savings
            if key not in x:
                x[str(key)] = [truetime]
            else:
                x[str(key)].append(truetime)
            if key not in y:
                y[str(key)] = [curr[key]['score']]
            else:
                y[str(key)].append(curr[key]['score'])
        if skip:
            continue
    data = []
    for key in x:
        try:
            temp_color = hex_to_rgb(colors[key])
        except KeyError:
            temp_color = hex_to_rgb("000000")
        # print(temp_color)
        trace = go.Scatter(
            x=x[key],
            y=y[key],
            name=key,
            line=dict(
                color=("rgb(" + str(temp_color[0]) + ", " + str(temp_color[1]) + ", " + str(temp_color[2]) + ")"),
                width=3,
                shape='hvh'
                )
        )
        data.append(trace)
    offline.plot(data, filename=filename, auto_open=False)


def create_gpa_graph(filename):
    files = os.listdir("data")
    x = []
    y = []
    skip = False
    for time in files:
        skip = False
        curr = load("data\\" + time)
        if "estimated_gpa" not in curr:
            continue
        inttime = int(time.replace(".db", ""))
        subtime = time_offset  # time to subtract
        truetime = datetime.datetime.fromtimestamp(inttime-subtime)  # minus is for timezone difference + daylight savings
        x.append(truetime)
        y.append(curr['estimated_gpa'])
        if skip:
            continue
    data = []
    trace = go.Scatter(
        x=x,
        y=y,
        name="Estimated_GPA",
        line=dict(
            color="rgb(0, 0, 0)",
            width=3,
            shape='hvh'
            )
    )
    data.append(trace)
    offline.plot(data, filename=filename, auto_open=False)


def hex_to_rgb(hexa):
    hexa = list(hexa)
    redl = []
    greenl = []
    bluel = []
    redl.append(hexa[0])
    redl.append(hexa[1])
    greenl.append(hexa[2])
    greenl.append(hexa[3])
    bluel.append(hexa[4])
    bluel.append(hexa[5])
    red = "".join(redl)
    blue = "".join(bluel)
    green = "".join(greenl)
    return [int(red, 16), int(green, 16), int(blue, 16)]


if __name__ == '__main__':
    # print(calc_total_gpa([97, 100, 100, 95, 99, 100, 100], [1, 0.5, 0.5, 0.5, 0.5, 0, 0]))
    # exit(0)

    # I use multiprocessing here so that it can terminate it if it takes too long to get grades. This fixes an issue
    # where it would freeze up previously.
    while True:
        while True:
            queue = multiprocessing.Queue()
            p = multiprocessing.Process(target=get_grades, args=(queue,))
            p.start()
            p.join(30)
            if p.is_alive():
                print("Getting grades has taken too long. Trying again.")
                p.terminate()
                p.join()
                continue
            break
        courses = queue.get()
        current = os.listdir("data")

        if len(current) >= 2 and courses == load("data\\" + current[-1]) == load("data\\" + current[-2]):
            print("No change in grades for " + student_name + ". Updating latest one at " + strftime("%Y-%m-%d %H:%M:%S.", localtime()))
            os.rename("data\\" + current[-1], "data\\" + str(int(time())) + ".db")
            create_graph(output)
            create_gpa_graph(output_gpa)
            print("Updated plots.")
        else:
            save(courses, "data\\" + str(int(time())) + ".db")
            print("Updated grades for " + student_name + " at " + strftime("%Y-%m-%d %H:%M:%S.", localtime()))
            create_graph(output)
            create_gpa_graph(output_gpa)
            print("Updated plots.")

        print("Waiting for one minute.")
        sleep(60)

