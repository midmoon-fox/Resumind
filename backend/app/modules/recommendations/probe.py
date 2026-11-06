"""Read-only live-source diagnostics and observed demo filters, never model calls."""

import re

from .source import matches


def observed_filters(jobs):
    """Find a demonstrable filter from actual source text, never invented vacancies.
    This is a diagnostic aid, not a replacement for the user's confirmed preferences.
    """
    for job in jobs:
        city = job["city"].strip() or ("Remote" if job["remote"] else None)
        if city is None:
            continue
        text = " ".join([job["title"], *job["job_types"], job["description_text"]])
        level = next(
            (
                word
                for word in (
                    "Junior",
                    "Senior",
                    "berufserfahren",
                    "Berufseinsteiger",
                    "Praktikum",
                    "Werkstudent",
                )
                if re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE)
            ),
            None,
        )
        direction = next((tag for tag in job["tags"] if tag.strip() and len(tag) <= 100), None)
        if direction is None:
            direction = next(
                (
                    word
                    for word in re.findall(r"[A-Za-z][A-Za-z+#.-]{2,}", job["title"])
                    if len(word) <= 100
                ),
                None,
            )
        if level and direction:
            filters = {"city": city, "direction": direction, "experienceLevel": level}
            if matches(job, filters):
                return filters
    return None


def probe(source):
    jobs = source.fetch()
    filters = observed_filters(jobs)
    samples = [job for job in jobs if filters and matches(job, filters)][:5]
    return {
        "provider": "arbeitnow",
        "sourceConfig": source.config_id,
        "sourceUrl": "https://www.arbeitnow.com/api/job-board-api",
        "sourceHome": "https://www.arbeitnow.com/",
        "modelCalls": False,
        "fetchedAt": jobs[0]["fetched_at"] if jobs else None,
        "jobsReceived": len(jobs),
        "locations": sorted({job["city"] for job in jobs}),
        "observedDemoFilters": filters,
        "matchingJobs": sum(matches(job, filters) for job in jobs) if filters else 0,
        "sampleJobs": [
            {
                "sourceJobId": job["source_job_id"],
                "title": job["title"],
                "company": job["company"],
                "city": job["city"],
                "sourceUrl": job["source_url"],
                "fetchedAt": job["fetched_at"],
                "publishedAt": job["published_at"],
                "sourceCreatedAt": job["source_created_at"],
                "availability": job["availability"],
            }
            for job in samples
        ],
    }
