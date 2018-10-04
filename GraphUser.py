from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from canvasapi.exceptions import InvalidAccessToken
import configparser
import os
from json.decoder import JSONDecodeError
import datetime
import calendar
import plotly.graph_objs as go
import plotly.offline as offline
import fileinput
from time import time, strftime, localtime
import multiprocessing
import json

API_URL = "https://stxavier.instructure.com/"


class GraphUser:
    parser = configparser.RawConfigParser()
    parser.read(r"config.txt")

    data_path = parser.get("AutoGrades_Config", "data_path")
    if "$id" not in data_path:
        raise Exception("\"$id\" is not in data path. Please fix the config.")

    line_path = parser.get("AutoGrades_Config", "line_path")
    if "$id" not in line_path:
        raise Exception("\"$id\" is not in line path. Please fix the config.")

    gpa_path = parser.get("AutoGrades_Config", "gpa_line_path")
    if "$id" not in gpa_path:
        raise Exception("\"$id\" is not in gpa line path. Please fix the config.")

    def __init__(self, api_key, public, id, name, email, data_path, line_path, gpa_path):
        self.api_key = api_key
        self.is_public = public
        self.id = id
        self.name = name
        self.email = email
        self.data_path = data_path
        self.db_path = data_path + "\\data"
        self.line_path = line_path
        self.gpa_path = gpa_path

    @classmethod
    def create_user(cls, api_key, public=False):
        canvas = Canvas(API_URL, api_key)
        id = canvas.get_current_user().get_profile()['id']
        name = canvas.get_current_user().get_profile()['name']
        email = canvas.get_current_user().get_profile()['primary_email']
        data_path = cls.data_path.replace("$id", str(id))
        line_path = cls.line_path.replace("$id", str(id))
        gpa_path = cls.gpa_path.replace("$id", str(id))
        if not os.path.isdir(data_path):
            if not os.path.isdir(cls.data_path.replace("$id", "")):
                os.mkdir(cls.data_path.replace("$id", ""))
            os.mkdir(data_path)
            os.mkdir(data_path + "\\data")

        graph_dir = os.path.dirname(line_path)
        if not os.path.exists(graph_dir):
            os.mkdir(graph_dir)

        # makes user config if it does not exist
        if not os.path.exists(data_path + "\\user_config.txt"):
            with open(data_path + "\\user_config.txt", "w"): pass

        parser = configparser.RawConfigParser()
        if not parser.has_section("User_Config"):
            parser.add_section("User_Config")
        parser["User_Config"] = {"api_key": api_key,
                                 "public": public,
                                 "id": id,
                                 "name": name,
                                 "email": email}
        with open(data_path + "\\user_config.txt", "w") as file:
            parser.write(file)

        return cls(api_key, public, id, name, email, data_path, line_path, gpa_path)

    @classmethod
    def get_user(cls, id):
        data_path = cls.data_path.replace("$id", str(id))
        if os.path.isdir(data_path):
            parser = configparser.RawConfigParser()
            parser.read(data_path + "\\user_config.txt")
            api_key = parser.get("User_Config", "api_key")
            # Checks if api_key is valid
            try:
                canvas = Canvas(API_URL, api_key)
                canvas.get_current_user()
            except InvalidAccessToken:
                print("Access token has expired. Continuing for now.")
                # TODO email user or something
            public = parser.get("User_Config", "public")
            name = parser.get("User_Config", "name")
            email = parser.get("User_Config", "email")
            line_path = cls.line_path.replace("$id", str(id))
            gpa_path = cls.gpa_path.replace("$id", str(id))
            return cls(api_key, public, id, name, email, data_path, line_path, gpa_path)
        else:
            raise NotADirectoryError("Given user ID \"" + str(id) + "\" is not currently stored in given data path.")

    def update_key(self, api_key):
        if self.api_key == api_key:
            print("No change in api_key when attempting to update. Ignoring.")
        # Checks if api_key is valid
        canvas = Canvas(API_URL, api_key)
        if canvas.get_current_user().get_profile()['id'] == self.id:
            self.api_key = api_key
            parser = configparser.RawConfigParser()
            parser.read(self.data_path + "\\user_config.txt")
            parser["User_Config"]["api_key"] = api_key
            with open(self.data_path + "\\user_config.txt", "w") as file:
                parser.write(file)
        else:
            raise InvalidAccessToken("Given api_key \"" + api_key + "\" is not to this account.")

    def get_course_names(self):
        canvas = Canvas(API_URL, self.api_key)
        courses = canvas.get_current_user().get_courses()
        course_names = []
        for course in courses:
            try:
                # print(course.attributes)
                if "access_restricted_by_date" in course.attributes and course.attributes["access_restricted_by_date"] is True:
                    continue
                elif "original_name" in course.attributes:
                    course_names.append(course.attributes["original_name"])
                elif "name" in course.attributes:
                    course_names.append(course.attributes["name"])
            except AttributeError:
                print("Attribute error while getting course name. Going to next one.")
                continue
        # print(dir(courses[1]))
        return course_names

    @staticmethod
    def round_traditional(val, digits):  # this function fixes problems with precision errors in rounding
        return round(val + 10 ** (-len(str(val)) - 1), digits)

    @staticmethod
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

    @staticmethod
    def calc_gpa_for_percent(percent, weight):
        if isinstance(percent, str):
            percent_num = int(GraphUser.round_traditional(float(percent.replace("%", "")), 0))
        elif isinstance(percent, float):
            percent_num = int(GraphUser.round_traditional(float(percent), 0))
        elif isinstance(percent, int):
            percent_num = percent
        else:
            print("Invalid type in percent.")
            return
        if percent_num >= 97:
            return GraphUser.round_traditional(4.33 + weight, 2)
        elif percent_num >= 70:
            unweighted_gpas = {70: 1.0, 71: 1.2, 72: 1.4, 73: 1.6, 74: 1.8, 75: 2.0, 76: 2.11, 77: 2.22, 78: 2.33,
                               79: 2.5, 80: 2.67, 81: 2.78, 82: 2.89, 83: 3.0, 84: 3.11, 85: 3.22, 86: 3.33, 87: 3.41,
                               88: 3.49, 89: 3.58, 90: 3.67, 91: 3.78, 92: 3.89, 93: 4.0, 94: 4.08, 95: 4.16, 96: 4.25}
            return GraphUser.round_traditional(unweighted_gpas[percent_num] + weight, 2)
        else:
            return GraphUser.round_traditional(weight, 2)

    @staticmethod
    def calc_total_gpa(courses, scores):
        gpas = []
        for course in courses:
            gpas.append(GraphUser.calc_gpa_for_percent(scores[course], courses[course]["weight"]))
        if len(gpas) == 0:
            print("Couldn't get any GPAs. This means that something is broken.")
            exit(1)
        final_gpa = GraphUser.round_traditional(sum(gpas) / float(len(gpas)), 2)
        return final_gpa

    @staticmethod
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

    def read_course_data(self):
        try:
            with open(self.data_path + "\\course_data.json", "r") as read_file:
                course_data = json.load(read_file)
            fixed_course_data = {}
        except FileNotFoundError:
            return {}
        for key in course_data:
            fixed_course_data[int(key)] = course_data[key]
        return fixed_course_data

    def write_course_data(self, course_data):
        with open(self.data_path + "\\course_data.json", "w") as write_file:
            json.dump(course_data, write_file, indent=4)

    def read_score_data(self, filename):
        with open(self.db_path + "\\" + str(filename), "r") as read_file:
            score_data = json.load(read_file)
        fixed_score_data = {}
        for key in score_data:
            if key == "estimated_gpa":
                fixed_score_data[key] = score_data[key]
            else:
                fixed_score_data[int(key)] = score_data[key]

        return fixed_score_data

    def write_score_data(self, score_data, filename):
        with open(self.db_path + "\\" + str(filename), "w") as write_file:
            json.dump(score_data, write_file, indent=4)

    def get_grades(self, queue):
        canvas = Canvas(API_URL, self.api_key)
        while True:
            try:
                color_data = canvas.get_current_user().get_colors()
            except JSONDecodeError:
                print("JSONDecodeError when getting colors. Trying again.")
                continue
            except CanvasException:
                print("CanvasException when getting colors. Trying again.")
                continue
            break
        courses = {}
        scores = {}
        while True:
            try:
                for course in list(canvas.get_courses(include=["total_scores", "current_grading_period_scores"])):
                    if "access_restricted_by_date" in course.attributes and course.attributes["access_restricted_by_date"] is True:
                        continue
                    # course_id = course.attributes['enrollments'][0].get('course_id')
                    course_id = course.id
                    # print(course_id)
                    score = course.attributes['enrollments'][0].get(
                        'current_period_computed_current_score')
                    total_score = course.attributes['enrollments'][0].get(
                        'computed_current_score')
                    if score is None and total_score is None:
                        continue
                    elif score is None:  # TODO this won't really work in Quarters 2 and 4. I'll have to come up with something else then.
                        score = total_score
                    period_name = course.attributes['enrollments'][0].get('current_grading_period_title')
                    if period_name is None or "Quarter" not in period_name:
                        continue

                    name = course.name
                    if "original_name" in course.attributes:
                        original_name = course.attributes['original_name']
                        name = course.attributes['name']
                    elif "name" in course.attributes:
                        original_name = course.attributes['name']
                        name = original_name
                    else:
                        print("Name does not exist. This shouldn't happen. Exiting!")
                        exit(1)
                    # TODO add functionality to only use selected courses
                    # print(name)

                    weight = 0
                    if "Accelerated" in original_name or "Honors" in original_name:
                        weight = 0.5
                    elif "AP" in original_name:
                        weight = 1

                    courses[course_id] = {"original_name": original_name, "name": name, "weight": weight, "color": color_data["custom_colors"]["course_" + str(course_id)].replace("#", "")}
                    scores[course_id] = score
                break
            except ConnectionError:
                print("ConnectionError while getting grades. Trying again.")
                continue
            except JSONDecodeError:
                print("Unexpected JSONDecodeError when getting grades. Trying again.")
                continue
        scores["estimated_gpa"] = GraphUser.calc_total_gpa(courses, scores)
        # out_data = [scores, estimated_gpa]
        disk_course_data = self.read_course_data()
        if disk_course_data != courses:
            # Here I'm overwriting the data for each course with the new data
            # I'm doing it this way so that a course that happens to have not been retrieved on this cycle won't get its data deleted
            for course_id in courses:
                disk_course_data[course_id] = courses[course_id]
            self.write_course_data(disk_course_data)
        queue.put(scores)

    def create_graph(self):
        files = os.listdir(self.db_path)
        course_data = self.read_course_data()
        x = {}
        y = {}
        for time in files:
            curr = self.read_score_data(time)
            for course_id in curr:
                if str(course_id) == "estimated_gpa":
                    continue
                inttime = int(time.replace(".json", ""))
                # this next line is a hacked together line of code that subtracts the local time from the utc time
                # to calculate the correct value here instead of me specifying it manually. This allows it to
                # automatically correct for daylight savings.
                subtime = int(round((calendar.timegm(datetime.datetime.now().utctimetuple()) - calendar.timegm(datetime.datetime.utcnow().utctimetuple())) / 10.0)) * 10
                truetime = datetime.datetime.fromtimestamp(inttime + subtime)  # minus is for timezone difference + daylight savings

                if course_id not in x:
                    x[course_id] = [truetime]
                else:
                    x[course_id].append(truetime)
                if course_id not in y:
                    y[course_id] = [curr[course_id]]
                else:
                    y[course_id].append(curr[course_id])
        data = []
        for course_id in x:
            try:
                temp_color = GraphUser.hex_to_rgb(course_data[course_id]["color"])
            except KeyError:
                temp_color = GraphUser.hex_to_rgb("000000")  # Default to black if colors are not available
            name = course_data[course_id]["name"]
            trace = go.Scatter(
                x=x[course_id],
                y=y[course_id],
                name=name,
                line=dict(
                    color=("rgb(" + str(temp_color[0]) + ", " + str(temp_color[1]) + ", " + str(temp_color[2]) + ")"),
                    width=3,
                    shape='hvh'
                )
            )
            data.append(trace)
        layout = go.Layout(showlegend=True)
        fig = go.Figure(data=data, layout=layout)
        if not os.path.exists(os.path.dirname(self.line_path)):
            os.mkdir(os.path.dirname(self.line_path))
        offline.plot(fig, filename=self.line_path, auto_open=False)
        with fileinput.FileInput(self.line_path, inplace=True) as file:
            for line in file:
                print(line.replace("<head>",
                                   "<head><script type=\"text/javascript\">setTimeout(function(){window.location.reload(1);}, 600000);</script>"),
                      end='')

    def create_gpa_graph(self):
        files = os.listdir(self.db_path)
        x = []
        y = []
        for time in files:
            curr = self.read_score_data(time)
            if "estimated_gpa" not in curr:
                continue
            inttime = int(time.replace(".json", ""))
            # this next line is a hacked together line of code that subtracts the local time from the utc time
            # to calculate the correct value here instead of me specifying it manually. This allows it to
            # automatically correct for daylight savings.
            subtime = int(round((calendar.timegm(datetime.datetime.now().utctimetuple()) - calendar.timegm(datetime.datetime.utcnow().utctimetuple())) / 10.0)) * 10
            truetime = datetime.datetime.fromtimestamp(inttime + subtime)  # minus is for timezone difference + daylight savings
            x.append(truetime)
            y.append(curr['estimated_gpa'])
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
        offline.plot(data, filename=self.gpa_path, auto_open=False)
        with fileinput.FileInput(self.gpa_path, inplace=True) as file:
            for line in file:
                print(line.replace("<head>",
                                   "<head><script type=\"text/javascript\">setTimeout(function(){window.location.reload(1);}, 600000);</script>"),
                      end='')

    def update_grade_graphs(self):
        # I use multiprocessing here so that it can terminate it if it takes too long to get grades. This fixes an issue
        # where it would freeze up previously.
        while True:
            queue = multiprocessing.Queue()
            p = multiprocessing.Process(target=self.get_grades, args=(queue,))
            p.start()
            p.join(30)
            if p.is_alive():
                print("Getting grades for " + self.name + " has taken too long. Trying again.")
                p.terminate()
                p.join()
                continue
            break
        scores = queue.get()
        try:
            current = os.listdir(self.db_path)
        except FileNotFoundError:
            os.mkdir(self.db_path)
            current = []

        if len(current) >= 2 and scores == self.read_score_data(current[-1]) == self.read_score_data(current[-2]):
            print("No change in grades for " + self.name + ". Updating latest one at " + strftime("%Y-%m-%d %H:%M:%S.", localtime()))
            os.rename(self.db_path + "\\" + current[-1], self.db_path + "\\" + str(int(time())) + ".json")
        else:
            self.write_score_data(scores, str(int(time())) + ".json")
            print("Updated grades for " + self.name + " at " + strftime("%Y-%m-%d %H:%M:%S.", localtime()))
        self.create_graph()
        self.create_gpa_graph()
        print("Updated plots for " + self.name + ".")


if __name__ == '__main__':
    pass
