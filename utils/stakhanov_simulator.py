from ia_scribe.tasks.task_scheduler import TaskScheduler
from ia_scribe.tasks.generic import taskify
from ia_scribe import scribe_globals
import logging, sys, threading, time, random
import matplotlib.pyplot as plt
import matplotlib.style as style
import numpy
style.use('seaborn-dark')

local_stats= []
system_stats = []

def setup_logger():
    log = logging.getLogger('Stakhanov Simulator')
    log.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(scribe_globals.LOGGING_FORMAT)
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.propagate = 0
    return log
logger = setup_logger()

counter_normal = 0
counter_hiprio = 0
counter_lowprio = 0
durations = [(0,0,0)]

def update_receiver(*args, **kwargs):
    #print 'received update', args, kwargs
    pass

task_scheduler = TaskScheduler()
task_scheduler.start()
time.sleep(1)

def stats_collector(scheduler, storage):
    while True:
        task_items = scheduler.get_all_tasks()
        datapoint =[
            time.time(),
            len([x for x in task_items if x['task'].state == 'pending']),
            len([x for x in task_items if x['task'].state == 'running']),
            len([x for x in task_items if x['task'].state == 'done']),
            len([x for x in task_items if x['level_name'] == 'high' and x['task'].state == 'running']),
            len([x for x in task_items if x['level_name'] == 'low' and x['task'].state == 'running']),
            len([x for x in task_items]),
            len([x for x in task_items if x['level_name'] == 'high' and x['task'].state == 'pending']),
            len([x for x in task_items if x['level_name'] == 'low' and x['task'].state == 'pending']),
        ]
        storage.append(datapoint)
        time.sleep(1)

def get_stats():
    return system_stats

def process_book(deltat):
    time.sleep(deltat)

def do_work(deltat):
    time.sleep(deltat)

def send_heartbeat():
    time.sleep(3)

def show_plot():

    def make_scatter_hist(fig):
        import matplotlib.gridspec as gridspec

        px, pz, py = list(zip(*durations))

        x = numpy.array(px)
        y = numpy.array(py)
        z = numpy.array(pz)

        gs = gridspec.GridSpec(3, 3)
        ax_main = plt.subplot(gs[1:3, :2])
        ax_xDist = plt.subplot(gs[0, :2], sharex=ax_main)
        ax_yDist = plt.subplot(gs[1:3, 2], sharey=ax_main)

        ax_main.scatter(x, y, c=z, marker='.')
        ax_main.set(xlabel="task duration", ylabel="this axis does not matter")

        ax_xDist.hist(x, bins=100, align='mid')
        ax_xDist.set(ylabel='count')
        ax_xCumDist = ax_xDist.twinx()
        ax_xCumDist.hist(x, bins=100, cumulative=True, histtype='step', normed=True, color='r', align='mid')
        ax_xCumDist.tick_params('y', colors='r')
        ax_xCumDist.set_ylabel('cumulative', color='r')

        ax_yDist.hist(y, bins=100, orientation='horizontal', align='mid')
        ax_yDist.set(xlabel='count')
        ax_yCumDist = ax_yDist.twiny()
        ax_yCumDist.hist(y, bins=100, cumulative=True, histtype='step', normed=True, color='r', align='mid',
                         orientation='horizontal')
        ax_yCumDist.tick_params('x', colors='r')
        ax_yCumDist.set_xlabel('cumulative', color='r')


    plt.ion()
    plt.show()
    f, ((ax1, ax2, ax3),( ax4, ax5, ax6), (ax7, ax8, ax9) ) \
        = plt.subplots(3, 3, figsize=(18,10),)
    plt.subplots_adjust(wspace=0.1, hspace=1)
    fig = plt.gcf()
    figueroa = plt.figure(figsize=(8, 8))
    fig.tight_layout()
    fig.suptitle("Task runtime system performance", fontsize=16)
    while True:
        stats = get_stats()
        x_axis = [x[0] for x in stats]
        y_waiting = [x[1] for x in stats]
        y_running = [x[2] for x in stats]
        y_results = [x[3] for x in stats]

        y_hiprio = [x[4] for x in stats]
        y_lowprio = [x[5] for x in stats]
        y_total = [x[6] for x in stats]

        y_queued_hiprio = [x[7] for x in stats]
        y_queued_loprio = [x[8] for x in stats]

        ax1.clear()
        ax2.clear()
        ax3.clear()
        ax4.clear()
        ax5.clear()
        ax6.clear()
        ax7.clear()
        ax8.clear()
        ax9.clear()

        ax1.plot(x_axis, y_waiting, 'black', label='waiting')
        ax1.set_title("Waiting")
        ax1.legend(loc='upper right')

        ax2.plot(x_axis, y_results, 'red', label='finished')
        ax2.set_title("Finished")
        ax2.legend(loc='upper left')

        ax3.plot(x_axis, y_waiting, 'black', label='waiting')
        ax3.plot(x_axis, y_running, 'blue', label='running')
        ax3.plot(x_axis, y_hiprio, 'green', label='hiprio')
        ax3.plot(x_axis, y_lowprio, 'purple', label='lowprio')
        ax3.set_title("Combined view")
        ax3.legend(loc='upper left')

        ax4.plot(x_axis, y_running, 'blue', label='running')
        ax4.set_title("Running")
        ax4.legend(loc='upper right')

        ax5.plot(x_axis, y_hiprio, 'green', label='hiprio')
        ax5.set_title("Running HIGH")
        ax5.legend(loc='upper right')

        ax6.plot(x_axis, y_lowprio, 'purple', label='lowprio')
        ax6.set_title("Running LOW")
        ax6.legend(loc='upper right')

        ax7.plot(x_axis, y_total, 'orange', label='normal')
        ax7.set_title("Total tasks")
        ax7.legend(loc='upper right')

        ax8.plot(x_axis, y_queued_hiprio, 'green', label='high')
        ax8.legend(loc='upper right')
        ax8.set_title("WAITING high")
        #ax8.set_ylim(ax8.get_ylim())

        ax9.plot(x_axis, y_queued_loprio, 'purple', label='long')
        ax9.legend(loc='upper right')
        ax9.set_title("WAITING low")
        #ax9.set_ylim(ax9.get_ylim())

        make_scatter_hist(figueroa)

        plt.draw()
        plt.pause(0.0001)


def test_high_load():
    while True:

        for k in range (1, 2):
            global counter_normal
            global counter_hiprio
            global counter_lowprio
            global durations
            counter_normal = 0
            counter_hiprio = 0
            counter_lowprio = 0
            print("+++++++++ scheduling do work")
            for i in range(1, random.randint(1, 20)):
                # Schedule normal tasks
                # generate ten random numbers (possivle durations)
                seeds = [random.uniform(0.1,6.1) for x in range(1, 20)]
                # either pick th eminimum or maximum
                duration = random.choice((max(seeds), min(seeds), min(seeds), min(seeds)))
                task = taskify(do_work, [duration], None,)
                task_scheduler.schedule(task, 'high')
                durations.append((duration, 'blue',  random.uniform(1.1, 5.5)))
                counter_normal += 1
            print("+++++++++ scheduling process books")
            for i in range(0, random.randint(0, 1)):
                # Schedule low priority tasks
                duration = random.randint(10, 20)
                task = taskify(process_book, [duration], None,)
                task_scheduler.schedule(task, 'low')
                durations.append((duration, 'green', random.uniform(3, 10.1)))
                counter_lowprio += 1
            print("+++++++++ scheduling heartbeats")
            for i in range(1, random.randint(0, 10)):
                # Schedule real time task
                duration = random.randint(0, 10)
                task = taskify(send_heartbeat, [], None,)
                task_scheduler.schedule(task, 'low')
                durations.append((duration, 'purple', 0, random.uniform(0.1, 1.1)))
                counter_hiprio += 1
        print("%%%%%%%%%%% sleeping")
        time.sleep(random.randint(1, 8))

        '''
        for i in range(1, 500):
            task = (do_work, [random.randint(0, 20)], None,)
            worker.waiting_tasks_queue.put(task)
            task = (send_heartbeat, [random.randint(0, 20)], None,)
            worker.waiting_tasks_queue.put(task)
        time.sleep(5)
        for i in range(1, 90):
            task = (send_heartbeat, [random.randint(0, 10)], None,)
            worker.waiting_tasks_queue.put(task)
            task = (send_heartbeat, [random.randint(0, 10)], None,)
            worker.waiting_tasks_queue.put(task)
            task = (send_heartbeat, [random.randint(0, 10)], None,)
            worker.waiting_tasks_queue.put(task)
        '''



stats_thread = threading.Thread(target=stats_collector, args=[task_scheduler, system_stats])
stats_thread.daemon = True
stats_thread.start()
print('started',stats_thread)


plott = threading.Thread(target=test_high_load)
plott.daemon = True
plott.start()


show_plot()
