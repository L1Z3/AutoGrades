from sys import exit
import os
import multiprocessing
from time import sleep
from GraphUser import GraphUser

if __name__ == '__main__':
    while True:
        p = []
        i = 0
        for user in os.listdir(GraphUser.data_path.replace("$id", "")):
            curr_user = GraphUser.get_user(int(user))
            p.append(multiprocessing.Process(target=curr_user.update_grade_graphs))
            p[i].start()
            i += 1
        print("\n\nStarted updating grades. Going again in one minute.")
        sleep(60)
        for j in p:
            if j.is_alive():
                print("A process took too long. It will be terminated.")
                j.terminate()
                j.join()
