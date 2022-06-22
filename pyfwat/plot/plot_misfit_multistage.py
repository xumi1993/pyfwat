import pygmt
from .plot_misfit import read_misfit
import numpy as np
import argparse


class PlotMulMisfit():
    def __init__(self, stages, norm=True):
        """Plot misfit with multi stages.

        Parameters
        ----------
        stages : list
            Stages information with 3 columns: start iteration, end iteration, column in misfit file to plot.
        """
        self.stages = stages
        self.read_stage_misfit(norm)
        self.colors = ['218/56/58', '47/127/193', '150/195/125', '196/151/178']

    def read_stage_misfit(self, norm=True):
        for i, stage in enumerate(self.stages):
            self.stages[i].append(np.array([read_misfit(iter, '*', col=stage[2]) for iter in range(stage[0], stage[1]+1)]))
        self.max_misfit = max([np.max(st[-1]) for st in self.stages])
        for i, stage in enumerate(self.stages):
            if norm:
                stage[-1] /= np.max(stage[-1])
        self.min_misfit = min([np.min(st[-1]) for st in self.stages])

    def plot(self, outpath='./figures'):
        fig = pygmt.Figure()
        # print(self.stages)
        bound = (self.stages[-1][1]-self.stages[0][0])*0.1
        if bound > 1:
            bound = 0.95
        bound_ms = ((self.max_misfit-self.min_misfit)/self.max_misfit)*0.1
        fig.basemap(region=[self.stages[0][0]-bound, self.stages[-1][1]+bound, self.min_misfit-bound_ms, 1+bound_ms],
                    projection="x0.5c/3c",
                    frame=['WSrt', 'xaf+l"Iteration"', 'yaf+l"Misfit"'])
        for i, stage in enumerate(self.stages):
            fig.plot(x=np.arange(stage[0], stage[1]+1), y=stage[-1], pen='0.5p')
            fig.plot(x=np.arange(stage[0], stage[1]+1), y=stage[-1], style='c0.25c', color=self.colors[i], pen='0.1p')
        fig.savefig('{}/misfit_M{:02d}_M{:02d}_multistages.png'.format(outpath, self.stages[0][0], self.stages[-1][1]))


def main():
    parser = argparse.ArgumentParser('Plot Misfit with multi stages')
    parser.add_argument('-m', help='start and end iteration nunbers e.g., 0/5,6/9,10/15',
                        metavar='it1_start/it1_end,it2_start/it2_end')
    parser.add_argument('-l', help='Columns in misfit files with iterations, defaults to 28,28,28',
                        metavar='col_num', default=None)
    parser.add_argument('-n', help='normlization with stages or iterations, defaults to iterations',
                        action='store_true')
    parser.add_argument('-c', help='Color of markers, defaults to 255/25/25', metavar='color', default='255/25/25')
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()
    its = [v.split('/') for v in args.m.split(',')]
    if args.l is None:
        cols = [28]*len(its)
    else:
        cols = [int(v) for v in args.l.split(',')]
    stages = [[int(st[0]), int(st[1]), col] for st, col in zip(its, cols)]
    pm = PlotMulMisfit(stages, norm=args.n)
    pm.plot(args.o)
        
            


