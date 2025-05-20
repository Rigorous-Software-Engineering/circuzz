import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import argparse
import os

def find(iterable, default=False, pred=None):
    """Returns the first true value in the iterable.

    If no true value is found, returns *default*

    If *pred* is not None, returns the first item
    for which pred(item) is true.

    """
    # first_true([a,b,c], x) --> a or b or c or x
    # first_true([a,b], x, f) --> a if f(a) else b if f(b) else x
    return next(filter(pred, iterable), default)

def geo_mean(iterable):
    a = np.array(iterable)
    return a.prod()**(1.0/len(a))

def negative_speedup(x, y):
    if x >= y:
        return x/y -1 # +/- 1 for aligning the axis
    elif x == 0:
        return 0 
    else:
        return -1*y/x +1 # +/- 1 for aligning the axis
    
def negative_speedup_geo(x, y):
    tmp = []
    for i, cfgval in enumerate(x):
        defval = y[i]
        if cfgval >= defval:
            tmp.append(cfgval/defval)
        # elif cfgval == 0:
        #     return 0 
        else:
            tmp.append(-1*defval/cfgval)
    return geo_mean(tmp)

def speedup_geo(x, y,cfg=''):
    tmp = []
    for i, cfgval in enumerate(x):
        defval = y[i]
        tmp.append(cfgval/defval)
    return geo_mean(tmp)  


def throughput_speedup_geo(circuits, times, circuitsdef, timesdef):
    throughputcfg = []
    throughputdef = []
    for i, x in enumerate(circuits):
        throughputcfg.append(x / times[i])
        throughputdef.append(circuitsdef[i] / timesdef[i])
    tmp = []
    for i, cfgval in enumerate(throughputcfg):
        defval = throughputdef[i]
        tmp.append(cfgval/defval)
    return geo_mean(tmp)  

######### parse input #########
parser = argparse.ArgumentParser(description='Plot pipeline stages.')
parser.add_argument('path', help="Path to the files with data named report-*cfg*.txt.")
parser.add_argument('--outdir', action="store", default=".", help="Output directory.")

args = parser.parse_args()

experiments = ['default', 'depth', 'asserts', 'inputs', 'outputs', 'notuning']
all = {'CIRCOM': { k: {'time': 0, 'tests': 0, 'seeds': 0, 'sat': 0} for k in experiments}, 

       'CORSET': { k: {'time': 0, 'tests': 0, 'seeds': 0, 'sat': 0} for k in experiments}, 

        'GNARK': { k: {'time': 0, 'tests': 0, 'seeds': 0, 'sat': 0} for k in experiments}, 

         'NOIR': { k: {'time': 0, 'tests': 0, 'seeds': 0, 'sat': 0} for k in experiments}}
all_geo = {'CIRCOM': { k: {'time': [], 'tests': [], 'seeds': [], 'sat': []} for k in experiments}, 

       'CORSET': { k: {'time': [], 'tests': [], 'seeds': [], 'sat': []} for k in experiments}, 

        'GNARK': { k: {'time': [], 'tests': [], 'seeds': [], 'sat': []} for k in experiments}, 

         'NOIR': { k: {'time': [], 'tests': [], 'seeds': [], 'sat': []} for k in experiments}}

# Example input
# # Effectiveness Comparison Table:
# # tool   & bug-id & seeds & time-median & circ-median
# # circom & 1      & 10    & 254.34      & 61.0
# # circom & 2      & 10    & 1859.64     & 567.0
# # circom & 3      & 10    & 809.6       & 210.0
# # circom & 4      & 10    & 439.08      & 107.5
# # corset & 5      & 10    & 17.28       & 10.5
# # corset & 6      & 10    & 19.59       & 17.0
# # corset & 7      & 10    & 215.24      & 90.5
# # corset & 8      & 10    & 206.5       & 111.5
# # gnark  & 9      & 10    & 687.9       & 122.0
# # gnark  & 10     & 10    & 792.51      & 141.0
# # gnark  & 11     & 10    & 836.63      & 162.0
# # gnark  & 12     & 5     & 3717.93     & 978
# # noir   & 13     & 9     & 2842.67     & 693
# # noir   & 14     & 2     & 7210.59     & 511.0
# # noir   & 15     & 10    & 2919.78     & 183.5

## Example input for sat inputs:
# # Summary (Paper Table 2):
# # tool   & bug-id & seeds & circ-SAT & time-min & time-median & time-max  & circ-min & circ-median & circ-max
# # \hline
# # \multirow{4}{*}{\circom}
# #  & \bug{1}   & 10     & 52.88\%   & 38s      & 4m14s       & 13m47s    & 7        & 61        & 212 \\
# #  & \bug{2}   & 10     & 57.84\%   & 13m08s    & 31m00s         & 1h00m30s     & 232      & 567       & 1265 \\
# #  & \bug{3}   & 10     & 57.38\%   & 43s      & 13m30s      & 35m17s    & 19       & 210       & 717 \\ 
# #  & \bug{4}   & 10     & 57.53\%   & 18s      & 7m19s       & 16m13s    & 8        & 108      & 247 \\

files = {'default': f"{args.path}/report-default.txt",
        'depth': f"{args.path}/report-depth.txt",
        'asserts': f"{args.path}/report-assert.txt",
        'inputs': f"{args.path}/report-inputs.txt",
        'outputs': f"{args.path}/report-outputs.txt",
        'notuning': f"{args.path}/report-notuning.txt"
        }
for cfg, file in files.items():
    tool = ''
    if not os.path.exists(file):
        continue
    with open(file, 'r') as f:
        lines = f.readlines()
        element = find(lines, "", lambda x: "Effectiveness Comparison Table" in x)
        index = lines.index(element)
        data = lines[index+2:index+17]

        for l in data:
            if not l or l=='\n':
                continue
            row = l.split('&')
            # print(row)
            tool = row[0].strip().upper()
            seeds = int(row[2].strip())
            time = float(row[3].strip())
            tests = float(row[4].strip())
            all[tool][cfg]['time'] += time
            all[tool][cfg]['seeds'] += seeds
            all[tool][cfg]['tests'] += tests
            all_geo[tool][cfg]['time'].append(time)
            all_geo[tool][cfg]['seeds'].append(seeds)
            all_geo[tool][cfg]['tests'].append(tests)

        # get SAT info
        element = find(lines, "", lambda x: "Summary (Paper Table 2):" in x)
        index = lines.index(element)
        data = lines[index+3:index+24]
        tool = ''

        for l in data:
            if not l or l=='\n':
                continue
            if 'multirow' in l:
                # \multirow{3}{*}{\noir} 
                l = l.strip()
                tool = l[17:-1].upper()
                continue

            row = l.split('&')
            if len(row) < 4:
                # the row with hline only
                continue

            sat_ins_str = row[3].strip().replace('%','').replace('\\','')
            sat_ins = float(sat_ins_str)

            all_geo[tool][cfg]['sat'].append(sat_ins)
            all[tool][cfg]['sat'] += sat_ins


######### compute speedup #########
time_speedup = {k:{y: speedup_geo(all_geo[k][y]['time'],all_geo[k]['default']['time']) for y in all_geo[k]} for k in all_geo}
circuits_speedup = {k:{y: speedup_geo(all_geo[k][y]['tests'],all_geo[k]['default']['tests']) for y in all_geo[k]} for k in all_geo}
sat_inputs_factor = {k:{y: speedup_geo(all_geo[k][y]['sat'],all_geo[k]['default']['sat']) for y in all_geo[k]} for k in all_geo}

all_times = {cfg:[] for cfg in experiments}
all_circuits = {cfg:[] for cfg in experiments}
all_sat_inputs = {cfg:[] for cfg in experiments}
for zkp in all_geo:
    for cfg in all_geo[zkp]:
        all_times[cfg] = all_times[cfg] + all_geo[zkp][cfg]['time']
        all_circuits[cfg] = all_circuits[cfg] + all_geo[zkp][cfg]['tests']
        all_sat_inputs[cfg] = all_sat_inputs[cfg] + all_geo[zkp][cfg]['sat']

time_over_all = {cfg: speedup_geo(all_times[cfg],all_times['default']) for cfg in all_times} 
circuits_over_all = {cfg: speedup_geo(all_circuits[cfg],all_circuits['default']) for cfg in all_circuits} 
throughput_over_all = {cfg: throughput_speedup_geo(all_circuits[cfg], all_times[cfg], all_circuits['default'], all_times['default']) for cfg in all_circuits} 
sat_inputs_over_all = {cfg: speedup_geo(all_sat_inputs[cfg],all_sat_inputs['default'],cfg) for cfg in all_sat_inputs} 


# print('\n\n Geo means')
# for x in time_over_all:
#     print(f"{x}: {time_over_all[x]}")

######################## plotting below ################
def namehalves(xpos, ylim, label):
    ax.text(xpos, ylim-5.2,
                label,
                ha='right', va='center', **hfont)
    
def autolabel(axis, bars, range=None):
    # attach some text labels
    for bar in bars:
        width = bar.get_width()
        offset = 1.1 if width > 0 else -1*range/25 # was range/8
        # offset = range/26 if width > 0 else -1*range/25 # was range/8
        label = "{:2.1f}x".format(width) if width > 0 else "{:2.1f}x".format(width)
        if width > 99:
            offset = -99#0.9*width
            axis.text(12, bar.get_y() + bar.get_height()/2,
                label,
                ha='right', va='center',  color='white', weight='bold', **hfont)
        else:
            axis.text(width+offset, bar.get_y() + bar.get_height()/2,
                    label,
                    ha='right', va='center', **hfont)

def autolabel_offbyone(axis, bars, range=None):
    # attach some text labels
    for bar in bars:
        width = bar.get_width()
        offset = range/8 if width > 0 else -1*range/25
        label = "{:2.1f}x".format(width+1) if width > 0 else "{:2.1f}x".format(width-1)
        if width > 99:
            offset = -99#0.9*width
            axis.text(width+offset, bar.get_y() + bar.get_height()/2,
                label,
                ha='right', va='center',  color='white', weight='bold', **hfont)
        else:
            axis.text(width+offset, bar.get_y() + bar.get_height()/2,
                    label,
                    ha='right', va='center', **hfont)
    
def hidefautolabel(axis, bars, range=None):
    # attach some text labels
    for bar in bars:
        width = bar.get_width()
        if width < 0.01 and width >-0.01:
            width = 0
        offset = range/10 if width >= 0 else -1*range/25
        label = "{:2.2f}x".format(width) if width >= 0 else "{:2.2f}x".format(width)
        axis.text(width+offset, bar.get_y() + bar.get_height()/2,
                label,
                ha='right', va='center', **hfont)
        
def hidefautolabel_offbyone(axis, bars, range=None):
    # attach some text labels
    for bar in bars:
        width = bar.get_width()
        if width < 0.01 and width >-0.01:
            width = 0
        offset = range/10 if width >= 0 else -1*range/25
        label = "{:2.2f}x".format(width+1) if width >= 0 else "{:2.2f}x".format(width-1)
        axis.text(width+offset, bar.get_y() + bar.get_height()/2,
                label,
                ha='right', va='center', **hfont)

def labelxticks(xticks, ints=False):
    xlabels = []
    for xt in xticks:
        xval = xt+1 if xt>=0 else xt-1
        if ints:
            xlabels.append(f'{xval:1.0f}')
        else:
            xlabels.append(f'{xval:1.1f}')
    return xlabels

fig, ax = plt.subplots()
width = 0.25
hfont = {'fontname': 'Helvetica','size': 14}
mpl.rc('font', family='Helvetica', size=14)
pipelines = list(all.keys())

ind = np.arange(5)

# list order explicitly, because Python dict does order of keys is nondeterministic
timeBar = ax.barh(ind - width, [time_over_all['depth'],
                                time_over_all['asserts'],
                                time_over_all['inputs'],
                                time_over_all['outputs'],
                                time_over_all['notuning']], width, color='red', label='time to bug')
circuitsBar = ax.barh(ind, [throughput_over_all['depth'],
                            throughput_over_all['asserts'],
                            throughput_over_all['inputs'],
                            throughput_over_all['outputs'],
                            throughput_over_all['notuning']], width, color='blue', label='test throughput')
satinsBar = ax.barh(ind+width, [sat_inputs_over_all['depth'],
                                sat_inputs_over_all['asserts'],
                                sat_inputs_over_all['inputs'],
                                sat_inputs_over_all['outputs'],
                                sat_inputs_over_all['notuning']], width, color='green', label='SAT inputs')

xrange = ax.get_xlim()
xwidth = xrange[1] - xrange[0]
autolabel(ax,timeBar, xwidth)
autolabel(ax,circuitsBar, xwidth)
autolabel(ax,satinsBar, xwidth)

ax.set_yticks(ind, labels=['expression\ndepth', 'asserts', 'inputs', 'outputs', 'target ratio\n$\\rho = 1$'], **hfont)
ax.invert_yaxis()  # labels read top-to-bottom
ax.set_xlim([0, xrange[1] + xwidth*0.18])
ax.legend(handles=[timeBar, circuitsBar, satinsBar], loc='lower right')
ax.spines['top'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines.right.set_position(('data', 0))
plt.savefig(f"{args.outdir}/figure6.pdf", format="pdf", bbox_inches="tight")
