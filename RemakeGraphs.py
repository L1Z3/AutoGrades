from GraphUser import GraphUser
import os
# This is a script to remake the graphs for a quarter without redoing the grades.
# To use for previous quarters, the config must be updated temporarily.

# loop through user IDs in data folder, assuming that folder that represents IDs
# is last folder in the data path, and update grades for each user
# TODO support data paths that don't have user ID as deepest subfolder
for user in os.listdir(GraphUser.data_path.replace("$id", "")):
    # get user object for current ID
    curr_user = GraphUser.get_user(int(user))
    curr_user.create_graph()
    curr_user.create_gpa_graph()