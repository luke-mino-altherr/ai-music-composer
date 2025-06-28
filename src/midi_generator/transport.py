"""Transport module for precise musical timing and sequence synchronization."""

import heapq
import platform
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from ..logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Use high-precision timer based on platform
if platform.system() == "Darwin":  # macOS
    time_get_time = time.time_ns
    logger.debug("Using macOS high-precision timer (time.time_ns)")
elif platform.system() == "Windows":
    time_get_time = time.perf_counter_ns
    logger.debug("Using Windows high-precision timer (time.perf_counter_ns)")
else:  # Linux and others

    def time_get_time():
        """Get nanosecond precision time on Linux/POSIX systems."""
        return time.clock_gettime(time.CLOCK_MONOTONIC) * 1_000_000_000

    logger.debug("Using Linux/POSIX high-precision timer (clock_gettime)")


@dataclass
class TimedEvent:
    """Represents a precisely timed musical event."""

    timestamp_ns: int  # Nanosecond precision timestamp
    callback: Callable
    event_id: Optional[int] = None  # Optional ID for event tracking/removal
    concurrent: bool = True  # Whether this event can be executed concurrently

    def __lt__(self, other):
        """Compare two events by timestamp for heap ordering."""
        return self.timestamp_ns < other.timestamp_ns


class PreciseTransport:
    """High-precision transport for musical timing."""

    NANOSECONDS_PER_MINUTE = 60_000_000_000

    def __init__(self, initial_bpm: float = 120.0, max_workers: int = 4):
        """Initialize the transport.

        Args:
            initial_bpm: Initial tempo in beats per minute
            max_workers: Maximum number of worker threads for concurrent
                callback execution
        """
        logger.debug(
            f"Initializing PreciseTransport with BPM: {initial_bpm}, "
            f"max_workers: {max_workers}"
        )
        self.bpm = initial_bpm
        self._ns_per_beat = self.NANOSECONDS_PER_MINUTE / initial_bpm
        self._is_playing = False
        self._current_beat = 0.0
        self._start_time_ns = 0
        self._stop_event = threading.Event()
        self._events = []  # heap queue of events
        self._transport_thread: Optional[threading.Thread] = None
        self._last_process_time = 0
        self._next_event_id = 0

        # Thread pool for concurrent callback execution
        self._max_workers = max_workers
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._active_futures: List[Future] = []

        # Lock for thread safety
        self._lock = threading.Lock()

        # Jitter thresholds for different warning levels
        self.GOOD_JITTER_NS = 500_000  # 0.5ms - good timing
        self.WARNING_JITTER_NS = 2_000_000  # 2ms - noticeable but acceptable
        self.CRITICAL_JITTER_NS = 5_000_000  # 5ms - problematic timing

        # Jitter monitoring
        self._jitter_stats = {"count": 0, "total_abs_jitter": 0, "max_jitter": 0}

        logger.debug(
            f"Transport initialized - ns_per_beat: {self._ns_per_beat}, "
            f"jitter thresholds: "
            f"good={self.GOOD_JITTER_NS/1_000_000:.1f}ms, "
            f"warning={self.WARNING_JITTER_NS/1_000_000:.1f}ms, "
            f"critical={self.CRITICAL_JITTER_NS/1_000_000:.1f}ms"
        )

    @property
    def current_beat(self) -> float:
        """Get the current beat position."""
        if not self._is_playing:
            logger.debug(
                f"Transport not playing, returning stored beat: "
                f"{self._current_beat}"
            )
            return self._current_beat
        elapsed_ns = time_get_time() - self._start_time_ns
        current_beat = elapsed_ns / self._ns_per_beat
        logger.debug(
            f"Transport playing - elapsed: {elapsed_ns}ns, "
            f"current_beat: {current_beat:.6f}"
        )
        return current_beat

    def _precise_wait_until(self, target_time_ns: int):
        """High precision wait implementation with adaptive strategy."""
        start_wait = time_get_time()

        while time_get_time() < target_time_ns:
            remaining_ns = target_time_ns - time_get_time()

            if remaining_ns > 10_000_000:  # More than 10ms remaining
                time.sleep(0.005)  # Sleep for 5ms chunks
            elif remaining_ns > 1_000_000:  # 1-10ms remaining
                time.sleep(0.0005)  # Sleep for 0.5ms
            elif remaining_ns > 100_000:  # 100μs-1ms remaining
                time.sleep(0.00005)  # Sleep for 50μs
            # else: busy wait for final <100μs for maximum precision

        wait_duration = time_get_time() - start_wait
        logger.debug(
            f"Precise wait completed - target: {target_time_ns}, "
            f"actual wait: {wait_duration}ns"
        )

    def _process_events(self):
        """Process events with high precision timing."""
        logger.debug("Starting event processing thread")
        events_processed = 0

        while not self._stop_event.is_set():
            now_ns = time_get_time()
            events_to_execute = self._collect_ready_events(now_ns)

            # Process events - execute immediately or submit to thread pool
            for event in events_to_execute:
                events_processed += 1
                self._handle_event_execution(event, now_ns)

            # Clean up completed futures periodically
            self._cleanup_completed_futures()

            # Wait for next event
            self._wait_for_next_event()

        logger.debug(
            f"Event processing thread stopped. Total events processed: "
            f"{events_processed}"
        )

    def _collect_ready_events(self, now_ns: int) -> List[TimedEvent]:
        """Collect all events that are ready to execute."""
        events_to_execute = []
        # Minimize lock time by collecting events in one pass
        with self._lock:
            while self._events and self._events[0].timestamp_ns <= now_ns:
                events_to_execute.append(heapq.heappop(self._events))
        return events_to_execute

    def _handle_event_execution(self, event: TimedEvent, now_ns: int):
        """Handle the execution of a single event with jitter tracking."""
        jitter = now_ns - event.timestamp_ns
        abs_jitter = abs(jitter)

        # Update jitter statistics
        self._update_jitter_stats(abs_jitter)

        # Log jitter based on severity
        self._log_jitter(event, jitter, abs_jitter)

        # Execute callback based on concurrency preference
        self._execute_event_callback(event)

    def _update_jitter_stats(self, abs_jitter: int):
        """Update jitter statistics."""
        self._jitter_stats["count"] += 1
        self._jitter_stats["total_abs_jitter"] += abs_jitter
        if abs_jitter > self._jitter_stats["max_jitter"]:
            self._jitter_stats["max_jitter"] = abs_jitter

    def _log_jitter(self, event: TimedEvent, jitter: int, abs_jitter: int):
        """Log jitter information based on severity."""
        if abs_jitter > self.CRITICAL_JITTER_NS:
            logger.error(
                f"CRITICAL timing jitter of {jitter/1_000_000:.3f}ms detected "
                f"for event {event.event_id} "
                f"(max: {self._jitter_stats['max_jitter']/1_000:.1f}μs)"
            )
            print(
                f"ERROR: Critical timing jitter of "
                f"{jitter/1_000_000:.3f}ms detected"
            )
        elif abs_jitter > self.WARNING_JITTER_NS:
            logger.warning(
                f"Noticeable timing jitter of {jitter/1_000_000:.3f}ms detected "
                f"for event {event.event_id} "
                f"(max: {self._jitter_stats['max_jitter']/1_000:.1f}μs)"
            )
            print(
                f"Warning: Noticeable timing jitter of "
                f"{jitter/1_000_000:.3f}ms detected"
            )
        elif abs_jitter > self.GOOD_JITTER_NS:
            logger.info(
                f"Acceptable timing jitter of {jitter/1_000_000:.3f}ms "
                f"for event {event.event_id}"
            )
        else:
            logger.debug(
                f"Event {event.event_id} executed with excellent jitter: "
                f"{jitter/1_000:.1f}μs"
            )

    def _execute_event_callback(self, event: TimedEvent):
        """Execute an event callback either in thread pool or immediately."""
        if event.concurrent and self._thread_pool:
            # Submit to thread pool for concurrent execution
            future = self._thread_pool.submit(self._execute_callback_safe, event)
            self._active_futures.append(future)
            logger.debug(f"Event {event.event_id} submitted to thread pool")
        else:
            # Execute immediately in timing thread for critical events
            self._execute_callback_safe(event)
            logger.debug(f"Event {event.event_id} executed immediately")

    def _wait_for_next_event(self):
        """Wait for the next event with appropriate timing strategy."""
        wait_time_ns = 1_000_000  # 1ms default wait

        # Check for next event and calculate wait time
        with self._lock:
            if self._events:
                next_event = self._events[0]
                wait_time_ns = next_event.timestamp_ns - time_get_time()
                if wait_time_ns > 0:
                    logger.debug(
                        f"Waiting {wait_time_ns/1_000_000:.3f}ms for next event "
                        f"{next_event.event_id}"
                    )

        # Wait outside the lock with appropriate strategy
        if wait_time_ns > 0:
            self._perform_wait(wait_time_ns)
        else:
            time.sleep(0.00005)  # Shorter sleep when no events (50μs)

    def _perform_wait(self, wait_time_ns: int):
        """Perform waiting with different strategies based on wait duration."""
        if wait_time_ns > 2_000_000:  # More than 2ms - use precise wait
            self._precise_wait_until(time_get_time() + wait_time_ns)
        elif wait_time_ns > 50_000:  # 50μs-2ms - hybrid approach
            # Sleep for most of the time, then busy wait
            sleep_time = (
                wait_time_ns - 50_000
            ) / 1_000_000_000  # Leave 50μs for busy wait
            if sleep_time > 0:
                time.sleep(sleep_time)
            # Busy wait for the final precision
            target_time = time_get_time() + 50_000
            while time_get_time() < target_time:
                pass
        else:
            # For very short waits (<50μs), busy wait for maximum precision
            target_time = time_get_time() + wait_time_ns
            while time_get_time() < target_time:
                pass

    def _execute_callback_safe(self, event: TimedEvent):
        """Safely execute an event callback with error handling."""
        try:
            event.callback()
            logger.debug(f"Event {event.event_id} callback executed successfully")
        except Exception as e:
            logger.error(f"Error executing event {event.event_id}: {e}")
            print(f"Error executing event: {e}")

    def _cleanup_completed_futures(self):
        """Remove completed futures from the active list."""
        initial_count = len(self._active_futures)
        self._active_futures = [f for f in self._active_futures if not f.done()]
        completed_count = initial_count - len(self._active_futures)
        if completed_count > 0:
            logger.debug(f"Cleaned up {completed_count} completed futures")

    def schedule_event(
        self, beat: float, callback: Callable, concurrent: bool = True
    ) -> int:
        """Schedule an event to occur at a specific beat.

        Args:
            beat: Beat position when the event should occur
            callback: Function to call at the specified beat
            concurrent: Whether the callback can be executed concurrently (default: True)

        Returns:
            Event ID that can be used to remove the event later
        """
        if not self._is_playing:
            logger.warning(
                f"Cannot schedule event at beat {beat}: transport not playing"
            )
            return -1

        event_id = self._next_event_id
        self._next_event_id += 1

        timestamp_ns = self._start_time_ns + int(beat * self._ns_per_beat)
        current_time_ns = time_get_time()

        # Check if this is an immediate event (already past due)
        if timestamp_ns <= current_time_ns:
            logger.debug(
                f"Event {event_id} at beat {beat} is immediate (past due by "
                f"{(current_time_ns - timestamp_ns)/1_000_000:.3f}ms)"
            )
            # Execute immediately in the calling thread to avoid scheduling delay
            try:
                callback()
                logger.debug(f"Immediate event {event_id} executed successfully")
                return event_id
            except Exception as e:
                logger.error(f"Error executing immediate event {event_id}: {e}")
                return event_id

        event = TimedEvent(
            timestamp_ns=timestamp_ns,
            callback=callback,
            event_id=event_id,
            concurrent=concurrent,
        )

        logger.debug(
            f"Scheduling event {event_id} at beat {beat} "
            f"(timestamp: {timestamp_ns}ns)"
        )

        with self._lock:
            heapq.heappush(self._events, event)
            logger.debug(
                f"Event {event_id} added to queue. Queue size: {len(self._events)}"
            )

        return event_id

    def remove_event(self, event_id: int) -> None:
        """Remove a scheduled event by its ID.

        Args:
            event_id: ID of the event to remove
        """
        logger.debug(f"Removing event {event_id}")
        with self._lock:
            initial_size = len(self._events)
            # Create new heap without the specified event
            self._events = [e for e in self._events if e.event_id != event_id]
            heapq.heapify(self._events)
            final_size = len(self._events)

            if initial_size != final_size:
                logger.debug(
                    f"Event {event_id} removed successfully. Queue size: "
                    f"{initial_size} -> {final_size}"
                )
            else:
                logger.warning(f"Event {event_id} not found in queue")

    def set_tempo(self, bpm: float):
        """Set the transport tempo.

        Args:
            bpm: New tempo in beats per minute
        """
        logger.debug(f"Setting tempo from {self.bpm} to {bpm} BPM")

        with self._lock:
            old_ns_per_beat = self._ns_per_beat
            self.bpm = bpm
            self._ns_per_beat = self.NANOSECONDS_PER_MINUTE / bpm

            logger.debug(
                f"Tempo changed from {old_ns_per_beat:.2f} to {bpm:.2f} BPM "
                f"(ns_per_beat: {self._ns_per_beat:.0f}ns)"
            )

            if self._is_playing:
                # Recalculate all future event timings
                old_events = self._events
                self._events = []
                now_ns = time_get_time()
                events_rescheduled = 0

                logger.debug(f"Rescheduling {len(old_events)} events for new tempo")

                for event in old_events:
                    if event.timestamp_ns > now_ns:
                        # Recalculate event timing based on new tempo
                        beat_position = (
                            event.timestamp_ns - self._start_time_ns
                        ) / old_ns_per_beat
                        new_timestamp = self._start_time_ns + int(
                            beat_position * self._ns_per_beat
                        )
                        new_event = TimedEvent(
                            timestamp_ns=new_timestamp,
                            callback=event.callback,
                            event_id=event.event_id,
                        )
                        heapq.heappush(self._events, new_event)
                        events_rescheduled += 1
                        logger.debug(
                            f"Event {event.event_id} rescheduled: "
                            f"{event.timestamp_ns} -> {new_timestamp}"
                        )

                logger.info(
                    f"Tempo changed to {bpm} BPM. Rescheduled "
                    f"{events_rescheduled} events"
                )

    def start(self):
        """Start the transport."""
        if self._is_playing:
            logger.warning("Transport start() called but already playing")
            return

        logger.info("Starting transport")
        self._is_playing = True
        self._start_time_ns = time_get_time()
        self._stop_event.clear()

        # Initialize thread pool for concurrent callback execution
        self._thread_pool = ThreadPoolExecutor(
            max_workers=self._max_workers, thread_name_prefix="transport-callback"
        )
        logger.debug(f"Thread pool initialized with {self._max_workers} workers")

        logger.debug(
            f"Transport started at beat {self._current_beat:.6f} " f"(BPM: {self.bpm})"
        )

        self._transport_thread = threading.Thread(target=self._process_events)
        self._transport_thread.start()
        logger.debug("Event processing thread started")

    def stop(self):
        """Stop the transport."""
        if not self._is_playing:
            logger.warning("Transport stop() called but not playing")
            return

        logger.info("Stopping transport")
        self._is_playing = False
        self._stop_event.set()

        if self._transport_thread:
            logger.debug("Waiting for event processing thread to stop")
            self._transport_thread.join()
            logger.debug("Event processing thread stopped")

        # Shutdown thread pool and wait for all callbacks to complete
        if self._thread_pool:
            logger.debug(
                f"Shutting down thread pool with {len(self._active_futures)} "
                f"active futures"
            )
            # Wait for currently executing callbacks to complete
            for future in self._active_futures:
                try:
                    future.result(timeout=1.0)  # Wait up to 1 second per callback
                except Exception as e:
                    logger.warning(f"Callback did not complete cleanly: {e}")

            self._thread_pool.shutdown(wait=True)
            self._thread_pool = None
            self._active_futures.clear()
            logger.debug("Thread pool shut down successfully")

        self._current_beat = self.current_beat
        logger.debug(f"Transport stopped at beat {self._current_beat:.6f}")

        # Clear pending events
        with self._lock:
            events_cleared = len(self._events)
            self._events = []
            logger.debug(f"Cleared {events_cleared} pending events")

    def reset(self):
        """Reset the transport to beat 0."""
        logger.debug("Resetting transport to beat 0")
        was_playing = self._is_playing
        if was_playing:
            logger.debug("Stopping transport for reset")
            self.stop()
        self._current_beat = 0.0
        logger.debug("Transport reset to beat 0")
        if was_playing:
            logger.debug("Restarting transport after reset")
            self.start()

    def get_jitter_stats(self) -> Dict:
        """Get timing jitter statistics.

        Returns:
            Dictionary containing jitter statistics
        """
        if self._jitter_stats["count"] == 0:
            return {"count": 0, "avg_jitter_us": 0, "max_jitter_us": 0}

        avg_jitter = (
            self._jitter_stats["total_abs_jitter"] / self._jitter_stats["count"]
        )
        return {
            "count": self._jitter_stats["count"],
            "avg_jitter_us": avg_jitter / 1_000,
            "max_jitter_us": self._jitter_stats["max_jitter"] / 1_000,
        }

    def get_thread_pool_stats(self) -> Dict:
        """Get thread pool statistics.

        Returns:
            Dictionary containing thread pool statistics
        """
        if not self._thread_pool:
            return {
                "active": False,
                "max_workers": self._max_workers,
                "active_futures": 0,
            }

        return {
            "active": True,
            "max_workers": self._max_workers,
            "active_futures": len(self._active_futures),
        }

    def schedule_critical_event(self, beat: float, callback: Callable) -> int:
        """Schedule a critical event that must execute immediately in timing thread.

        Critical events bypass the thread pool and execute in the main timing
        thread to ensure minimal latency. Use for time-sensitive operations.

        Args:
            beat: Beat position when the event should occur
            callback: Function to call at the specified beat

        Returns:
            Event ID that can be used to remove the event later
        """
        return self.schedule_event(beat, callback, concurrent=False)
