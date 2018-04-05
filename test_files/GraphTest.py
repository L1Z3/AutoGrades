import plotly.plotly as py
import plotly.graph_objs as go
import plotly.offline as offline
import pickle
import os
import datetime

# Create random data with numpy
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

random_x = [1506994205, 1507125275, 1507128921, 1507143488, 1507147127, 1507168972, 1507172684, 1507216364, 1507220003, 1507293079, 1507296729, 1507314939, 1507318580, 1507475619, 1507665935, 1507833514, 1507852589]
i = 0
for thing in random_x:
    random_x[i] = datetime.datetime.fromtimestamp(thing)
    i += 1
english = [94.51, 94.51, 94.79, 94.79, 94.88, 94.88, 94.88, 94.88, 94.88, 94.88, 95.06, 95.06, 95.06, 95.06, 96.50, 94.84, 94.84]
biology = [99.04, 99.04, 99.04, 99.04, 99.04, 99.04, 99.48, 99.48, 99.48, 99.48, 99.48, 99.48, 99.48, 99.48, 99.48, 99.32, 99.32]
spanish = [100.61, 100.61, 100.61, 100.61, 100.61, 100.61, 100.61, 100.61, 100.61, 100.61, 100.61, 100.61, 100.52, 100.52, 100.55, 99.97, 99.97]
#
# data = load('data.db')
# for key in data:
#     random_x.append(key)
#     random_y.append(data[key]['Algebra']['score'])



# Create a trace
trace = go.Scatter(
    x=random_x,
    y=english,
    name="English"
)
trace2 = go.Scatter(
    x=random_x,
    y=biology,
    name="Biology"
)
trace3 = go.Scatter(
    x=random_x,
    y=spanish,
    name="Spanish"
)

data = [trace, trace2, trace3]

# py.iplot(data, filename='basic-line')
offline.plot(data, filename='current_line.html')
