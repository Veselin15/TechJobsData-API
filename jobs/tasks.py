import logging
import re
import subprocess
from celery import shared_task
from datetime import timedelta
from django.utils import timezone
from .models import Job

logger = logging.getLogger(__name__)

SCRAPER_CWD = "/app/scraper_service"


def _log_scrapy_output(spider_label, output):
    """Log Scrapy stats so we can see item counts and HTTP status codes."""
    item_match = re.search(r"'item_scraped_count':\s*(\d+)", output)
    dropped_match = re.search(r"'item_dropped_count':\s*(\d+)", output)
    item_count = int(item_match.group(1)) if item_match else 0
    dropped_count = int(dropped_match.group(1)) if dropped_match else 0

    status_matches = re.findall(
        r"'downloader/response_status_count/(\d+)':\s*(\d+)", output
    )
    if status_matches:
        statuses = ", ".join(f"{code}×{count}" for code, count in status_matches)
        logger.info("[%s] HTTP responses: %s", spider_label, statuses)

    logger.info("[%s] items scraped=%s, dropped=%s", spider_label, item_count, dropped_count)

    if item_count == 0:
        for line in output.strip().splitlines()[-15:]:
            logger.warning("  [%s] %s", spider_label, line.strip())

    return item_count


def _run_scrapy(spider_args, timeout=120, label=None):
    """Run a scrapy crawl subprocess and return item_scraped_count."""
    label = label or spider_args[-1]
    cmd = ["scrapy", "crawl", *spider_args]
    result = subprocess.run(
        cmd,
        cwd=SCRAPER_CWD,
        timeout=timeout,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    item_count = _log_scrapy_output(label, output)

    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    return item_count


@shared_task
def run_scrapers(keyword='Python', location='Europe'):
    """
    On-Demand Task: Triggered when a user clicks 'Search' or 'Scrape'.
    Runs LinkedIn for the specific keyword AND grabs the latest WWR feed.
    """
    results = []

    try:
        logger.info("🚀 [On-Demand] Starting WWR Scrape...")
        _run_scrapy(["wwr"], timeout=60, label="wwr")
        results.append("WWR")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode(errors='replace') if isinstance(e.stderr, bytes) else (e.stderr or "")
        logger.error("❌ [On-Demand] WWR Scraper Failed: %s", error_msg)
    except subprocess.TimeoutExpired:
        logger.error("⚠️ [On-Demand] WWR Scraper Timed Out")

    try:
        logger.info("🔍 [On-Demand] Starting LinkedIn Scrape for %s...", keyword)
        _run_scrapy(
            ["linkedin", "-a", f"keyword={keyword}", "-a", f"location={location}"],
            timeout=180,
            label=f"linkedin:{keyword}",
        )
        results.append("LinkedIn")
    except subprocess.TimeoutExpired:
        logger.warning("⚠️ Scrape for %s timed out! Process killed.", keyword)
        return "LinkedIn Scrape Timed Out"
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode(errors='replace') if isinstance(e.stderr, bytes) else (e.stderr or "")
        logger.error("❌ LinkedIn Scrape Failed: %s", error_msg)
    except Exception as e:
        logger.error("❌ LinkedIn Scrape Failed: %s", e)

    return f"Scraping Finished. Sources: {', '.join(results)}"


@shared_task
def run_bulk_scrape():
    """
    Scheduled Task: Runs periodically (e.g., every 6 hours).
    Populates the database with a wide variety of jobs from ALL sources.
    """
    results = []

    def run_spider(spider_name, timeout=120):
        try:
            logger.info("🚀 [Bulk] Starting %s...", spider_name)
            _run_scrapy([spider_name], timeout=timeout, label=spider_name)
            results.append(spider_name)
            logger.info("✅ [Bulk] %s Finished", spider_name)
        except subprocess.TimeoutExpired:
            logger.error("⚠️ [Bulk] %s Timed Out", spider_name)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode(errors='replace') if isinstance(e.stderr, bytes) else (e.stderr or "")
            logger.error("❌ [Bulk] %s Failed: %s", spider_name, error_msg)

    run_spider("wwr")
    run_spider("remoteok")
    run_spider("pyjobs")
    run_spider("themuse")
    run_spider("glassdoor", timeout=600)

    tech_stack = ["Python", "JavaScript", "React", "DevOps", "Java"]
    regions = ["Remote", "Europe", "United States"]

    for tech in tech_stack:
        for region in regions:
            task_name = f"LI:{tech}-{region}"
            try:
                _run_scrapy(
                    ["linkedin", "-a", f"keyword={tech}", "-a", f"location={region}"],
                    timeout=300,
                    label=task_name,
                )
                results.append(task_name)
            except subprocess.TimeoutExpired:
                logger.warning("[Bulk] %s timed out", task_name)
            except Exception as e:
                logger.warning("[Bulk] %s failed: %s", task_name, e)

    final_report = f"Bulk Scrape Complete. Covered: {', '.join(results)}"
    logger.info(final_report)
    return final_report


@shared_task
def cleanup_old_jobs():
    """
    Janitor Task: Deletes jobs posted more than 30 days ago.
    """
    cutoff_date = timezone.now().date() - timedelta(days=30)
    deleted_count, _ = Job.objects.filter(posted_at__lt=cutoff_date).delete()

    msg = f"🧹 Janitor: Deleted {deleted_count} jobs older than {cutoff_date}"
    logger.info(msg)
    return msg
