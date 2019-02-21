from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from canvasapi.exceptions import InvalidAccessToken
import configparser
import os
from json.decoder import JSONDecodeError
import datetime
import calendar
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import plotly.graph_objs as go
import plotly.offline as offline
import fileinput
from time import time, strftime, localtime
import multiprocessing
import json
from helper import *

# API url for St. Xavier's Canvas
API_URL = "https://stxavier.instructure.com/"


# Each instance of this class is a specific student that has their grades tracked with my system
class GraphUser:
    # Read config from config.txt
    parser = configparser.RawConfigParser()
    parser.read(r"config.txt")

    # TODO use specific exceptions when "$id" is not in the path?
    # get data path from config
    data_path = parser.get("AutoGrades_Config", "data_path")
    if "$id" not in data_path:
        raise Exception("\"$id\" is not in data path. Please fix the config.")

    # get output graph path from config, with "$id" the student ID
    line_path = parser.get("AutoGrades_Config", "line_path")
    if "$id" not in line_path:
        raise Exception("\"$id\" is not in line path. Please fix the config.")

    # get output GPA graph path from config, with "$id" the student ID
    gpa_path = parser.get("AutoGrades_Config", "gpa_line_path")
    if "$id" not in gpa_path:
        raise Exception("\"$id\" is not in gpa line path. Please fix the config.")

    # constructor for GraphUser; probably shouldn't be called directly--use create_user or get_user instead
    def __init__(self, api_key, public, id, name, email, data_path, line_path, gpa_path):
        """
        Constructor for GraphUser object.
        Takes a variety of information about the user to construct the object.
        It probably shouldn't be called directly, but through create_user() or get_user() instead.
        """
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
        """
        Adds a user to be tracked.

        :param api_key: API key for user to add
        :param public: Specify whether user's grades should be publicly shown.
        :return: GraphUser object of new user.
        """
        # Create Canvas object with inputted API key
        canvas = Canvas(API_URL, api_key)

        # get basic information about user
        id = canvas.get_current_user().get_profile()['id']
        name = canvas.get_current_user().get_profile()['name']
        email = canvas.get_current_user().get_profile()['primary_email']

        # make paths specific to ID of current user
        data_path = cls.data_path.replace("$id", str(id))
        line_path = cls.line_path.replace("$id", str(id))
        gpa_path = cls.gpa_path.replace("$id", str(id))

        # create data path if it doesn not exist
        if not os.path.isdir(data_path):
            if not os.path.isdir(cls.data_path.replace("$id", "")):
                os.mkdir(cls.data_path.replace("$id", ""))
            os.mkdir(data_path)
            os.mkdir(data_path + "\\data")

        # make graph folder if it doesn't exist
        graph_dir = os.path.dirname(line_path)
        if not os.path.exists(graph_dir):
            os.mkdir(graph_dir)

        # make user config if it does not exist
        if not os.path.exists(data_path + "\\user_config.txt"):
            with open(data_path + "\\user_config.txt", "w"): pass

        # initalize config parser object
        parser = configparser.RawConfigParser()

        # if the config doesn't exist, create it
        if not parser.has_section("User_Config"):
            parser.add_section("User_Config")

        # put information into config
        parser["User_Config"] = {"api_key": api_key,
                                 "public": public,
                                 "id": id,
                                 "name": name,
                                 "email": email}

        # write the config to disk
        with open(data_path + "\\user_config.txt", "w") as file:
            parser.write(file)

        return cls(api_key, public, id, name, email, data_path, line_path, gpa_path)

    @classmethod
    def get_user(cls, id):
        """
        Makes user object of already-added user

        :param id: Canvas ID of user
        :return: GraphUser object for user with inputted ID
        """
        # get data path for specific user
        data_path = cls.data_path.replace("$id", str(id))

        # check if the data path exists, and raise an exception if it doesn't
        # (because this method is for getting an already-added user)
        if os.path.isdir(data_path):
            # initialize config parser object
            parser = configparser.RawConfigParser()
            # read user config
            parser.read(data_path + "\\user_config.txt")
            # get API key from config
            api_key = parser.get("User_Config", "api_key")
            # Check if api_key is valid
            while True:
                try:
                    canvas = Canvas(API_URL, api_key)
                    canvas.get_current_user()
                except InvalidAccessToken:
                    print("Access token has expired. Trying again for now.")
                    # TODO email user or something
                    continue
                except ConnectionError:
                    print("ConnectionError while getting user info from Canvas. Trying again.")
                    continue
                break

            # get basic info about user from config
            public = parser.get("User_Config", "public")
            name = parser.get("User_Config", "name")
            email = parser.get("User_Config", "email")
            if parser.has_option("User_Config", "custom_line_path_id"):
                custom_line_path_id = parser.get("User_Config", "custom_line_path_id")
                line_path = cls.line_path.replace("$id", custom_line_path_id)
                gpa_path = cls.gpa_path.replace("$id", custom_line_path_id)
            else:
                line_path = cls.line_path.replace("$id", str(id))
                gpa_path = cls.gpa_path.replace("$id", str(id))

            return cls(api_key, public, id, name, email, data_path, line_path, gpa_path)
        else:
            raise NotADirectoryError("Given user ID \"" + str(id) + "\" is not currently stored in given data path.")

    def update_key(self, api_key):
        """
        Updates the API key for a user

        :param api_key: New API key
        :return: None
        """
        # ignore if API key that you're attempting to change to is the same as the saved one
        if self.api_key == api_key:
            print("No change in api_key when attempting to update. Ignoring.")
            return

        canvas = Canvas(API_URL, api_key)
        # Check if api_key is valid, raise exception if it isn't
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
        """
        Gets a list of course names for the current user.

        :return: List of course names as strings
        """
        canvas = Canvas(API_URL, self.api_key)
        # get courses for current user
        courses = canvas.get_current_user().get_courses()
        course_names = []
        # loop through courses
        for course in courses:
            try:
                # ignore the course if it's restricted
                if "access_restricted_by_date" in course.attributes and course.attributes["access_restricted_by_date"] is True:
                    continue
                # If there exists an original_name attribute, that means that the name attribute is a nickname.
                # Use original name if available, otherwise use name, which is the original name when the original_name
                # attribute doesn't exist.
                elif "original_name" in course.attributes:
                    course_names.append(course.attributes["original_name"])
                elif "name" in course.attributes:
                    course_names.append(course.attributes["name"])
            except AttributeError:
                print("Attribute error while getting course name. Going to next one.")
                continue
        return course_names

    def read_course_data(self):
        """
        Reads the stored data about the courses for the current user.

        :return: Dictionary of data about courses for current user
        """
        try:
            # open the json file and read it
            with open(self.data_path + "\\course_data.json", "r") as read_file:
                course_data = json.load(read_file)
            fixed_course_data = {}
        # if there's no course data yet, just return an empty dictionary
        except FileNotFoundError:
            return {}
        # Convert the course_data keys from being stored as strings (as JSON requires)
        # to being stored as ints (as has been previously established in my program)
        for key in course_data:
            fixed_course_data[int(key)] = course_data[key]
        return fixed_course_data

    def write_course_data(self, course_data):
        """
        Writes the given course_data to course_data json file for current user

        :param course_data: Course data to store, as a dictionary
        :return: None
        """
        with open(self.data_path + "\\course_data.json", "w") as write_file:
            json.dump(course_data, write_file, indent=4)

    def read_score_data(self, filename):
        """
        Reads score data for a specific filename

        :param filename: Filename as string in format of "[unix time].json", e.g. "1538614994.json"
        :return: Dictionary of scores for each course at specified time, along with estimated GPA
        """
        # load json from disk
        with open(self.db_path + "\\" + str(filename), "r") as read_file:
            score_data = json.load(read_file)
        fixed_score_data = {}

        # Convert the course_data keys from being stored as strings (as JSON requires)
        # to being stored as ints (as has been previously established in my program)
        for key in score_data:
            if key == "estimated_gpa":
                fixed_score_data[key] = score_data[key]
            else:
                fixed_score_data[int(key)] = score_data[key]
        return fixed_score_data

    def write_score_data(self, score_data, filename):
        """
        Writes the given score_data to json file for current user with given filename

        :param score_data: Score data to store, as a dictionary
        :param filename: Filename as string in format of "[unix time].json", e.g. "1538614994.json"
        :return: None
        """
        with open(self.db_path + "\\" + str(filename), "w") as write_file:
            json.dump(score_data, write_file, indent=4)

    @staticmethod
    def get_grading_periods(course):
        """
        Gets grading periods for a course.

        This method is modeled after similar ones in the Canvas API, but the canvas
        API does not have one for listing grading periods, so here we are.
        :param course: Course object to get grading periods for
        :return: List of dictionaries of grading periods.
        """
        response = course._requester.request(
            'GET',
            'courses/{}/grading_periods'.format(course.id)
        ).json()

        return response['grading_periods']

    @staticmethod
    def get_grading_period(course, period_name):
        """
        Gets the grading period ID of a specific period name for a course.

        :param course: Course object to get period for
        :param period_name: Name of grading period
        :return: ID for grading period with given name; -1 if grading period is not found
        """
        for period_dict in GraphUser.get_grading_periods(course):
            # print(str(period_dict["title"]) + "\t" + str(period_name))
            if period_dict["title"] == period_name:
                return int(period_dict["id"])
        return -1

    def get_grades(self, queue, period=None):
        """
        Retrieves grades and course data for current user from Canvas, and formats them as dictionaries.

        :param queue: Something that needs to be in here for multiprocessing to work properly.
                      (I don't know, I just watched a YouTube tutorial)
        :param period: String for name of grading period to get grades for. Default is using the current grading period.
        :return: None (returns through queue instead of traditional return)
        """
        canvas = Canvas(API_URL, self.api_key)
        # Get custom course colors, trying again on exception
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
        # Loop for trying to get grades, in place so that it can try again after an exception
        while True:
            try:
                # Loop through all courses for the particular user, and include scores in that retrieval
                for course in list(canvas.get_courses(include=["total_scores", "current_grading_period_scores"])):
                    # If the course can't be accessed by the user because it has been date restricted,
                    # ignore that course.
                    if "access_restricted_by_date" in course.attributes and course.attributes["access_restricted_by_date"] is True:
                        continue
                    # Assign course ID from course attribute to variable course_id
                    course_id = course.id

                    # set name to the course attribute name
                    name = course.name
                    # If the original name attribute exists, that means that there is a nickname in use.
                    if "original_name" in course.attributes:
                        # in this case, set original name variable to original name attribute
                        original_name = course.attributes['original_name']
                        # and name variable to (nick)name attribute
                        name = course.attributes['name']
                    # If original name attribute doesn't exist, that means there's no nickname
                    elif "name" in course.attributes:
                        # in this case, just use name for both original_name and name
                        original_name = course.attributes['name']
                        name = original_name
                    else:
                        print("Name does not exist. This shouldn't happen. Exiting!")
                        raise NameError

                    # Get the current grading period id from Canvas if not specified by the user
                    if period is None:
                        period_id = course.attributes['enrollments'][0].get('current_grading_period_id')
                    # Get the ID of the specified grading period
                    else:
                        period_id = GraphUser.get_grading_period(course, period)
                    # Skip if the specified grading period isn't found
                    if period_id == -1:
                        continue

                    # Get list of enrollment objects for the current course
                    # that are for the current user and the specified grading period id
                    course_enrollments = list(course.get_enrollments(user_id=self.id, grading_period_id=period_id))
                    if len(course_enrollments) == 0:
                        continue
                    current_enrollment = course_enrollments[0]

                    if name == "PE S1":
                        print(name + "\t" + str(current_enrollment.grades))
                        print(name + "\t" + str(course.attributes['enrollments'][0]))

                    # If there is no grade for the current course, skip it.
                    if current_enrollment is None or "current_score" not in current_enrollment.grades or current_enrollment.grades["current_score"] is None:
                        continue
                    score = current_enrollment.grades["current_score"]

                    # If the class is an Honors(/Accelerated) class, then the weight is 0.5
                    if "Accelerated" in original_name or "Honors" in original_name:
                        weight = 0.5
                    # If the class is an AP class, then the weight is 1
                    elif "AP" in original_name:
                        weight = 1
                    # by default, there's a zero GPA weight on the class
                    else:
                        weight = 0
                    # assign dictionary containing course information for current course to key that is the course id
                    courses[course_id] = {"original_name": original_name, "name": name, "weight": weight, "color": color_data["custom_colors"]["course_" + str(course_id)].replace("#", "")}

                    # assign score for current course to corresponding ID in scores dictionary
                    scores[course_id] = score
                break
            except ConnectionError:
                print("ConnectionError while getting grades. Trying again.")
                continue
            except JSONDecodeError:
                print("Unexpected JSONDecodeError when getting grades. Trying again.")
                continue

        # put the estimated gpa in the scores dictionary
        scores["estimated_gpa"] = calc_total_gpa(courses, scores)
        # Read the currently stored course data
        disk_course_data = self.read_course_data()
        # if there's been a change in the course data, the update it
        if disk_course_data != courses:
            # Here I'm overwriting the data for each course with the new data

            # I'm doing it this way so that a course that happens to have not been
            # retrieved on this cycle won't get its data deleted
            for course_id in courses:
                disk_course_data[course_id] = courses[course_id]
            self.write_course_data(disk_course_data)
        queue.put(scores)

    def create_graph(self):
        """
        Creates a graph of the changes in grades over time for the current user.

        :return: None
        """
        # List of data files for the user (as in, grades for user at each period in time)
        files = os.listdir(self.db_path)
        # Read course data from disk
        course_data = self.read_course_data()
        # Dictionary for x values (with key as course ID and value as the list of unix times that data exists for)
        x = {}
        # Dictionary for y values (with key as course ID and value as list for scores for that course at each time)
        y = {}
        # Loop through data files (i.e. times that data exists for)
        for time in files:
            # Dictionary containing score data at the current time
            current_score_data = self.read_score_data(time)
            # for the current time, loop through every course ID that has a stored score
            for course_id in current_score_data:
                # if the estimated gpa is encountered, skip it
                if str(course_id) == "estimated_gpa":
                    continue
                # removes the file extension and converts the unix time to an integer (this is in UTC)
                inttime = int(time.replace(".json", ""))
                # this next line is a hacked together line of code that subtracts the local time from the utc time
                # to calculate the correct value here instead of me specifying it manually. This allows it to
                # automatically correct for daylight savings.
                # (subtime is the difference between UTC and the unix time adjusted for timezone and daylight savings)
                subtime = int(round((calendar.timegm(datetime.datetime.now().utctimetuple()) - calendar.timegm(datetime.datetime.utcnow().utctimetuple())) / 10.0)) * 10
                # The way this works also probably means that after a daylight-savings change,
                # the displayed times on the graph that were before the change are probably off.
                # I have not tested this yet, but I'm pretty sure it will happen
                # TODO figure this out
                # truetime is local unix time for given UTC time (i.e. adjusted for timezone and daylight savings)
                truetime = datetime.datetime.fromtimestamp(inttime + subtime)

                # if the course id doesn't already have an x value, create a list with the current time
                if course_id not in x:
                    x[course_id] = [truetime]
                # if the course id does have an x value, append the current time to the list
                else:
                    x[course_id].append(truetime)
                # if the course id doesn't already have a y value, create a list with the current score
                if course_id not in y:
                    y[course_id] = [current_score_data[course_id]]
                # if the course id does have a y value, append the current score to the list
                else:
                    y[course_id].append(current_score_data[course_id])
        data = []
        # iterate through sets of x values for each course
        for course_id in x:
            if "color" in course_data[course_id]:
                # Get color to use for this specific course from course data
                temp_color = hex_to_rgb(course_data[course_id]["color"])
            else:
                # Default to black if colors are not available
                temp_color = hex_to_rgb("FFFFFF")
            # set local variable name to name of course from course data
            name = course_data[course_id]["name"]
            # create a line with plotly for the current course ID
            trace = go.Scatter(
                x=x[course_id],
                y=y[course_id],
                name=name,
                line=dict(
                    color=("rgb(" + str(temp_color[0]) + ", " + str(temp_color[1]) + ", " + str(temp_color[2]) + ")"),
                    width=3,
                    # this shape looks best for the grade graphs in my opinion
                    # It uses vertical lines in between two values that have changed to signify that
                    # there's no gradual increase or decrease in grades, but sudden rises and falls
                    shape='hvh'
                )
            )
            # add the line for current course ID to final graph data
            data.append(trace)
        # layout specifying to show the legend
        # this makes it show the legend even when there's only one course being tracked
        # (it only shows the legend when two or more courses are on the graph without this line)
        layout = go.Layout(showlegend=True)
        # DARK THEME, OH YES
        layout.template = "plotly_dark"
        # create final graph object with plotly
        fig = go.Figure(data=data, layout=layout)
        # make the graph directory if it doesn't exist, just in case
        if not os.path.exists(os.path.dirname(self.line_path)):
            os.mkdir(os.path.dirname(self.line_path))
        # create the graph with plotly
        offline.plot(fig, filename=self.line_path, auto_open=False)
        # add in javascript to the graph file so that it automatically refreshes every 10 minutes on the client side
        with fileinput.FileInput(self.line_path, inplace=True) as file:
            for line in file:
                print(line.replace("<head>",
                                   "<head><script type=\"text/javascript\">setTimeout(function(){window.location.reload(1);}, 600000);</script>"),
                      end='')

    def create_gpa_graph(self):
        """
        Creates a graph for the changes in estimated GPA over time for the current user.

        Much of this method is the same as the normal create_graph() method.
        I may consider combining the methods at some point.
        :return: None
        """
        # List of data files for the user (as in, grades for user at each period in time)
        files = os.listdir(self.db_path)
        # List of times
        x = []
        # List of GPAs
        y = []
        # Loop through data files (i.e. times that data exists for)
        for time in files:
            current_score_data = self.read_score_data(time)
            # if the estimated gpa is not in the current data file, skip it
            if "estimated_gpa" not in current_score_data:
                continue
            # removes the file extension and converts the unix time to an integer (this is in UTC)
            inttime = int(time.replace(".json", ""))
            # this next line is a hacked together line of code that subtracts the local time from the utc time
            # to calculate the correct value here instead of me specifying it manually. This allows it to
            # automatically correct for daylight savings.
            # (subtime is the difference between UTC and the unix time adjusted for timezone and daylight savings)
            subtime = int(round((calendar.timegm(datetime.datetime.now().utctimetuple()) - calendar.timegm(datetime.datetime.utcnow().utctimetuple())) / 10.0)) * 10
            # The way this works also probably means that after a daylight-savings change,
            # the displayed times on the graph that were before the change are probably off.
            # I have not tested this yet, but I'm pretty sure it will happen
            # TODO figure this out
            # truetime is local unix time for given UTC time (i.e. adjusted for timezone and daylight savings)
            truetime = datetime.datetime.fromtimestamp(inttime + subtime)
            # add current time to x values
            x.append(truetime)
            # add current estimated gpa to y values
            y.append(current_score_data['estimated_gpa'])
        data = []
        # Make a line for estimated gpa
        trace = go.Scatter(
            x=x,
            y=y,
            name="Estimated_GPA",
            line=dict(
                color="rgb(255, 255, 255)",
                width=3,
                shape='hvh'
            )
        )
        # Add estimated gpa line to final graph data
        data.append(trace)
        layout = go.Layout()
        # DARK THEME, OH YES
        layout.template = "plotly_dark"
        fig = go.Figure(data=data, layout=layout)
        # Make GPA graph
        offline.plot(fig, filename=self.gpa_path, auto_open=False)
        # add in javascript to the graph file so that it automatically refreshes every 10 minutes on the client side
        with fileinput.FileInput(self.gpa_path, inplace=True) as file:
            for line in file:
                print(line.replace("<head>",
                                   "<head><script type=\"text/javascript\">setTimeout(function(){window.location.reload(1);}, 600000);</script>"),
                      end='')

    def update_grade_graphs(self):
        """
        Controls the rest of the class.

        It gets the grades using get_grades() and multiprocessing, and then updates the grade graphs.
        It also prints basic information out to the console.
        :return: None
        """
        # I use multiprocessing here so that it can terminate it if it takes too long to get grades. This fixes an issue
        # where it would freeze up previously.
        while True:
            queue = multiprocessing.Queue()
            p = multiprocessing.Process(target=self.get_grades, args=(queue, "Quarter 3"))
            p.start()
            # Terminate get_grades() if it takes more than 30 seconds to complete
            p.join(30)
            if p.is_alive():
                print("Getting grades for " + self.name + " has taken too long. Trying again.")
                p.terminate()
                p.join()
                continue
            break
        # get scores from get_grades() process
        scores = queue.get()
        # list the data files if the data path exists, create the path if it doesn't exist
        if os.path.exists(self.db_path):
            data_list = os.listdir(self.db_path)
        else:
            os.mkdir(self.db_path)
            data_list = []

        # if the scores gotten on this round are the same as the last two score updates,
        if len(data_list) >= 2 and scores == self.read_score_data(data_list[-1]) == self.read_score_data(data_list[-2]):
            print("No change in grades for " + self.name + ". Updating latest one at " + strftime("%Y-%m-%d %H:%M:%S.", localtime()))
            # then just rename the last score update to the current time.
            os.rename(self.db_path + "\\" + data_list[-1], self.db_path + "\\" + str(int(time())) + ".json")
        else:
            # if the scores gotten on this round are different, then write them to disk with the current time.
            self.write_score_data(scores, str(int(time())) + ".json")
            print("Updated grades for " + self.name + " at " + strftime("%Y-%m-%d %H:%M:%S.", localtime()))
        # Make the grade and GPA graphs with the current data.
        self.create_graph()
        self.create_gpa_graph()
        print("Updated plots for " + self.name + ".")


# Do nothing if the file is ran directly.
# (I keep this in here in case I want to add functionality on a direct run.)
if __name__ == '__main__':
    pass
