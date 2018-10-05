from sys import exit
import os
import multiprocessing
from time import sleep
from GraphUser import GraphUser

# Only run if ran directly through this file
if __name__ == '__main__':
    # Loop through grade cycle infinitely
    while True:
        # list of processes
        p = []

        i = 0

        # loop through user IDs in data folder, assuming that folder that represents IDs
        # is last folder in the data path, and update grades for each user
        # TODO support data paths that don't have user ID as deepest subfolder
        for user in os.listdir(GraphUser.data_path.replace("$id", "")):
            # get user object for current ID
            curr_user = GraphUser.get_user(int(user))
            # start updating grades for current ID
            p.append(multiprocessing.Process(target=curr_user.update_grade_graphs))
            p[i].start()
            i += 1

        # console output to indicate that the program is starting to update grades
        print("\n\nStarted updating grades. Going again in one minute.")
        sleep(60)

        # if after 60 seconds, one of the processes is still updating grades for a user, kill it
        for j in p:
            if j.is_alive():
                print("A process took too long. It will be terminated.")
                j.terminate()
                j.join()
