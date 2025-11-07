"""Trading scheduler for LLM-based automated trading."""

from __future__ import annotations

import schedule
import time
import threading
from datetime import datetime, time as dt_time
from typing import Callable, Optional

from ..utils.logger import get_logger


class TradingScheduler:
    """Scheduler for running trading tasks at specified intervals."""
    
    def __init__(self) -> None:
        """Initialize the trading scheduler."""
        self.logger = get_logger(self.__class__.__name__)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
    def schedule_trading(
        self,
        trading_function: Callable[[], None],
        interval_minutes: int = 60,
        market_hours_only: bool = True,
        timezone: str = "America/New_York",
    ) -> None:
        """Schedule trading function to run at specified intervals.
        
        Args:
            trading_function: Function to execute for trading
            interval_minutes: Interval in minutes between executions
            market_hours_only: Whether to run only during market hours
            timezone: Timezone for market hours
        """
        self.logger.info(
            f"Scheduling trading every {interval_minutes} minutes"
            f"{' (market hours only)' if market_hours_only else ''}"
        )
        
        if market_hours_only:
            # Schedule during market hours (9:30 AM - 4:00 PM ET, Monday-Friday)
            schedule.every().monday.at("09:30").do(self._schedule_market_hours_trading, trading_function, interval_minutes)
            schedule.every().day.at("09:30").do(self._schedule_market_hours_trading, trading_function, interval_minutes)
        else:
            # Schedule continuously
            schedule.every(interval_minutes).minutes.do(trading_function)
    
    def _schedule_market_hours_trading(
        self,
        trading_function: Callable[[], None],
        interval_minutes: int
    ) -> None:
        """Helper to schedule trading during market hours."""
        # Cancel any existing jobs
        schedule.clear()
        
        # Schedule jobs for today
        now = datetime.now()
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        
        if now.time() < market_open:
            # Before market open - schedule first run at open
            schedule.every().day.at("09:30").do(trading_function)
            schedule.every(interval_minutes).minutes.do(trading_function).tag("trading")
        elif now.time() < market_close:
            # During market hours - schedule next run
            schedule.every(interval_minutes).minutes.do(trading_function).tag("trading")
        
        # Schedule stop at market close
        schedule.every().day.at("16:00").do(self._stop_daily_trading)
    
    def _stop_daily_trading(self) -> None:
        """Stop trading for the day."""
        schedule.clear("trading")
        self.logger.info("Market closed - stopping daily trading")
    
    def start(self) -> None:
        """Start the scheduler in a separate thread."""
        if self._running:
            self.logger.warning("Scheduler is already running")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()
        self.logger.info("Trading scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return
        
        self.logger.info("Stopping trading scheduler...")
        self._running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        schedule.clear()
        self.logger.info("Trading scheduler stopped")
    
    def _run_scheduler(self) -> None:
        """Run the scheduler loop."""
        while self._running and not self._stop_event.is_set():
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    def is_running(self) -> bool:
        """Check if the scheduler is running.
        
        Returns:
            True if scheduler is running, False otherwise
        """
        return self._running
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time.
        
        Returns:
            Next run time or None if no jobs scheduled
        """
        jobs = schedule.jobs
        if not jobs:
            return None
        
        next_job = min(jobs, key=lambda job: job.next_run)
        return next_job.next_run
    
    def list_scheduled_jobs(self) -> list:
        """List all scheduled jobs.
        
        Returns:
            List of scheduled job information
        """
        jobs_info = []
        for job in schedule.jobs:
            jobs_info.append({
                "function": str(job.job_func),
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "interval": str(job.interval),
                "unit": job.unit,
            })
        return jobs_info