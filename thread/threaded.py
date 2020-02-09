"""Module for support of threaded execution"""
import logging
import threading
import time


class Timer:
    """Simple timer class"""
    def __init__(self):
        "Timer constructor"
        self.timings = []
    def reset(self):
        """Replace latest tic, if present"""
        if self.timings:
            self.timings.pop()
        self.tic()
    def peek_toc(self):
        """Get toc without popping tic"""
        return self.now() - self.timings[0]
    def tic(self):
        """Start a new timing"""
        self.timings.append(self.now())
    def toc(self):
        """Get timing on latest tic"""
        return self.now() - self.timings.pop(0)
    def now(self):
        """Get current datetime"""
        # return datetime.now()
        return time.time()


class AbstractThread:
    """Abstract wrapper for a python thread
    """
    counter = 0
    running_lock = None
    is_running = True
    name = ""
    def __init__(self, function, is_daemon=False, name=""):
        self.thread_function = function
        self.is_daemon = is_daemon
        self.running_lock = threading.Lock()
        self.name = name

    def run(self):
        self.thread = threading.Thread(target=self.looped_thread_function, daemon=self.is_daemon)
        self.is_running = True
        self.thread.start()

    def looped_thread_function(self):
        # get a local running variable
        is_running = True
        while is_running:
            # run the thread function
            self.thread_function()
            # safely update the local value
            with self.running_lock:
                is_running = self.is_running

    def stop(self):
        # print(f"{self.name} Thread abt to get running lock to stop")
        with self.running_lock:
            # print(f"{self.name} Thread got running lock and stopping.")
            self.is_running = False
        print(f"{self.name} Thread released running lock, releasing can-run.")
        # release other potentially holding the thread
        self.can_run.set()
        print(f"{self.name} Thread released running lock, releasing args.")
        self.can_access_args.set()
        print(f"{self.name} Thread released running lock joining")
        self.thread.join()
        print(f"{self.name} Thread joined.")


class TimingThread(AbstractThread):
    """Thread to measure time and notify timed thread"""
    can_run = None
    can_access_args = None
    is_delaying = None
    is_auto_resetting = False
    executed = False

    arg_buffer = None

    def reset(self):
        """Unset locks and reset the timers
        """
        if self.is_delaying is not None:
            self.is_delaying.clear()
        self.can_run.clear()
        self.timer.reset()
        self.executed = False
        self.arg_buffer = []

    def initialize_locks(self, can_run, can_access_args=None, is_delaying=None):
        # see if there's an event lock for the delay section
        self.can_run = can_run
        self.can_access_args = can_access_args
        self.is_delaying = is_delaying

    def __init__(self, delay,  can_run, can_access_args=None, is_delaying=None, sleep_delta=1, auto_reset=True):
        super().__init__(self.thread_run, name="Timing")
        self.timer = Timer()
        self.delay = delay
        self.is_auto_resetting = auto_reset
        self.sleep_delta = sleep_delta
        self.initialize_locks(can_run, can_access_args, is_delaying)
        self.reset()
        self.executed = False

    def set_args(self, args):
        """Gain access to the task arguments
        """
        self.timed_thread_args = args

    def update_arg_buffer(self, new_args):
        """Updates the arguments used by the timed thread
        """
        self.arg_buffer.append(new_args)

    def update_args(self):
        """Update the arguments used by the task thread"""
        self.can_access_args.wait()
        self.can_access_args.clear()
        self.timed_thread_args["args"] = self.arg_buffer.pop()
        self.can_access_args.set()

    def thread_run(self):
        # print(f"{threading.get_ident()} Entered timing thread run function")

        # update arguments, if needed
        if self.arg_buffer:
            self.update_args()

        delta = self.timer.peek_toc()
        # print("Toc:", self.timer.peek_toc(), "now:", self.timer.now(), "delta:", delta)

        if self.executed:
            time.sleep(self.sleep_delta)
            return

        if delta < self.delay:
            if self.is_delaying is not None:
                # mark that the thread is in delay
                self.is_delaying.set()
            # print(f"{threading.get_ident()} Timing thread sleeping cause delta is {delta} and delay has to be >= {self.delay}.")
            time.sleep(self.sleep_delta)
        else:
            # print(f"{threading.get_ident()} Timing thread breaking sleep cause delta is {delta} and delay has to be >= {self.delay}.")
            if self.is_delaying is not None:
                # mark that the thread is in delay
                self.is_delaying.clear()
            # permit the timed thread to run
            self.can_run.set()
            if self.is_auto_resetting:
                # reset self-timer automatically
                self.timer.reset()
            self.executed = True

class TimedThread(AbstractThread):
    can_access_args = None
    """Abstract runnable class for timed threaded execution"""
    def __init__(self, function, can_run, can_access_args=None, args=None,  use_args=False, result=None):
        super().__init__(self.thread_run, name="Timed")
        self.can_run = can_run
        self.can_access_args = can_access_args
        self.function = function
        self.args = args
        self.use_args = use_args or self.args
        self.result = result

    def thread_run(self):
        """Run the thread"""
        # print(f"{threading.get_ident()} Timed thread running the func!, flag is: {self.can_run.is_set()}")
        if self.can_run is not None:
            # wait for unblocked condition
            self.can_run.wait()
        # run the assigned function
        # print(self.args)
        if self.use_args:
            if self.can_access_args is not None:
                self.can_access_args.wait()
                self.can_access_args.clear()
            res = self.function(self.args["args"])
            if self.can_access_args is not None:
                self.can_access_args.set()
        else:
            res = self.function()
        self.result.append(res)
        # disable self
        self.can_run.clear()


class TimedThreadRunner:
    """Abstract manager class for threaded execution"""
    delay_time = None
    can_run = None
    delaying_event = None
    can_access_args = None
    args= None
    delay_function = None

    def make_args(self, args):
        """Argument wrapper to enable updating"""
        return {"args": args}

    def __init__(self, function, args=None):
        self.function = function
        self.args = self.make_args(args)
        self.can_run, self.can_access_args = threading.Event(), threading.Event()
        self.can_run.set()
        self.can_access_args.set()
        self.running = False
        self.result = []

    def set_delay(self, delay_time, delay_func=None, delay_func_args=None):
        """Set delay in milliseconds"""
        # create a condition object to block the thread
        self.delay_time = delay_time
        if delay_func is not None:
            self.delaying_event = threading.Event()
            self.delay_function = delay_func
            self.delay_function_args = self.make_args(delay_func_args)

    def run_now(self):
        """Manually force the thread to perform its function"""
        self.can_run.set()

    def reset_time(self, new_args=None):
        """Reset the delay counter"""
        if self.running:
            self.timing_thread.reset()
            self.timing_thread.update_arg_buffer(new_args)
        else:
            # not started yet -- do it now
            if new_args is not None:
                self.args = self.make_args(new_args)
            self.start()

    def update_args(self, args, do_restart=False):
        """Update the arguments to the running thread"""
        if self.delay_time is None:
            # if running without a delay mechanism
            self.args = self.make_args(args)
            # restart the task thread if specified
            if do_restart:
                self.start()
        else:
            # if running with a delay mechanism, reset the time and inform the timer thread
            self.reset_time(args)

    def start(self):
        # reset results
        self.result = []
        self.threads = []
        """Starts the assigned function in a separate thread"""
        if self.delay_time is None:
            # unlock
            self.can_run.set()
            # start a standard threaded run
            self.thread = TimedThread(self.function, args=self.args, can_run=self.can_run, can_access_args=self.can_access_args, result=self.result)
            self.start_thread(self.thread)
        else:
            # lock the event
            self.can_run.clear()
            # run the (blocked) task thread
            self.thread = TimedThread(self.function, args=self.args, can_run=self.can_run, can_access_args=self.can_access_args, result=self.result)
            self.start_thread(self.thread)

            # setup the delay function, if any
            if self.delay_function is not None:
                # setup another timed thread for it
                self.delaying_event.clear()
                self.delay_thread = TimedThread(self.delay_function, args=self.delay_function_args, can_run=self.delaying_event, result=[])
                self.start_thread(self.delay_thread)
            # run a timer thread
            self.timing_thread = TimingThread(self.delay_time, self.can_run, self.can_access_args, self.delaying_event)
            self.timing_thread.set_args(self.args)
            self.start_thread(self.timing_thread)
        self.running = True

    def start_thread(self, thread):
        thread.run()
        self.threads.append(thread)
        # print(f"Adding thread, now total: {len(self.threads)}.")

    def stop(self):
        """Stop the threaded function"""
        print(f"Stopping {len(self.threads)} threads")
        while self.threads:
            thread = self.threads.pop()
            thread.stop()
        print(f"Thread pool empty.")
        self.can_run.set()
        self.can_access_args.set()
        if self.delaying_event is not None:
            self.delaying_event.set()

    def get_result(self):
        """Result fetcher function"""
        if self.result:
            self.result = self.result[0]
        return self.result
    # def start(self):
    #     """Starts the threaded function"""
    #     self.thread.join()

# test
def main_test():
    def func(args):
        print("****Function running!****")
        print("Args:", args)

    print("RUnning..")
    manager = TimedThreadRunner(func, "catter")
    manager.set_delay(3)
    manager.start()
    while True:
        if input("Press R to reset\n") == "R":
            manager.reset_time("doggerbank")
        if input("Press R to reset\n") == "S":
            manager.stop()
            break

    print("Main thread is Done!")

if __name__ == '__main__':
    main_test()
