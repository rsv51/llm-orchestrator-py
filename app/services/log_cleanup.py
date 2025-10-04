"""
Log cleanup service for periodic maintenance of request logs.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logger import get_logger
from app.core.config import settings
from app.models.request_log import RequestLog

logger = get_logger(__name__)


class LogCleanupService:
    """Service for cleaning up old request logs."""
    
    def __init__(
        self,
        retention_days: int = 30,
        cleanup_interval_hours: int = 24
    ):
        """
        Initialize log cleanup service.
        
        Args:
            retention_days: Number of days to retain logs (default: 30)
            cleanup_interval_hours: Hours between cleanup runs (default: 24)
        """
        self.retention_days = retention_days
        self.cleanup_interval_hours = cleanup_interval_hours
        self._running = False
    
    async def cleanup_old_logs(
        self,
        db: Optional[AsyncSession] = None
    ) -> dict:
        """
        Delete logs older than retention period.
        
        Args:
            db: Optional database session (creates new one if not provided)
            
        Returns:
            Dictionary with cleanup statistics
        """
        close_db = False
        if db is None:
            db = AsyncSessionLocal()
            close_db = True
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            
            # Count logs to be deleted
            count_query = select(RequestLog).where(RequestLog.created_at < cutoff_date)
            result = await db.execute(count_query)
            logs_to_delete = len(result.scalars().all())
            
            if logs_to_delete == 0:
                logger.info("No old logs to clean up")
                return {
                    "deleted_count": 0,
                    "cutoff_date": cutoff_date.isoformat(),
                    "retention_days": self.retention_days
                }
            
            # Delete old logs
            delete_query = delete(RequestLog).where(RequestLog.created_at < cutoff_date)
            await db.execute(delete_query)
            await db.commit()
            
            logger.info(
                f"Cleaned up {logs_to_delete} old request logs",
                extra={
                    "deleted_count": logs_to_delete,
                    "cutoff_date": cutoff_date.isoformat(),
                    "retention_days": self.retention_days
                }
            )
            
            return {
                "deleted_count": logs_to_delete,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": self.retention_days
            }
        
        except Exception as e:
            logger.error(f"Log cleanup failed: {str(e)}", exc_info=True)
            await db.rollback()
            raise
        
        finally:
            if close_db:
                await db.close()
    
    async def run_periodic_cleanup(self):
        """Run cleanup task periodically in background."""
        self._running = True
        logger.info(
            f"Starting periodic log cleanup service "
            f"(retention: {self.retention_days} days, "
            f"interval: {self.cleanup_interval_hours} hours)"
        )
        
        while self._running:
            try:
                # Perform cleanup
                result = await self.cleanup_old_logs()
                logger.info(f"Periodic cleanup completed: {result}")
                
                # Wait for next cleanup interval
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
            
            except asyncio.CancelledError:
                logger.info("Log cleanup service cancelled")
                break
            
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {str(e)}", exc_info=True)
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    def stop(self):
        """Stop the cleanup service."""
        self._running = False


# Global cleanup service instance
_cleanup_service: Optional[LogCleanupService] = None


async def start_log_cleanup_service(
    retention_days: int = 30,
    cleanup_interval_hours: int = 24
):
    """
    Start the log cleanup background service.
    
    Args:
        retention_days: Number of days to retain logs
        cleanup_interval_hours: Hours between cleanup runs
    """
    global _cleanup_service
    
    if _cleanup_service is not None:
        logger.warning("Log cleanup service already running")
        return
    
    _cleanup_service = LogCleanupService(
        retention_days=retention_days,
        cleanup_interval_hours=cleanup_interval_hours
    )
    
    await _cleanup_service.run_periodic_cleanup()


def stop_log_cleanup_service():
    """Stop the log cleanup service."""
    global _cleanup_service
    
    if _cleanup_service is not None:
        _cleanup_service.stop()
        _cleanup_service = None