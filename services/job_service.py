import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from core.database import db
from models.job import JobCreate
from services.distance import haversine_distance, calculate_eta


def create_job(job_data: JobCreate, customer_id: str, current_user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    job_id = f"job_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    user_name = job_data.customerName
    user_phone = job_data.customerPhone

    if not user_name:
        if current_user and current_user.get("name") and current_user.get("name") != "Priya Sharma":
            user_name = current_user.get("name")
        else:
            db_user = db.get_document("users", customer_id)
            if db_user and db_user.get("name"):
                user_name = db_user.get("name")

    if not user_phone:
        if current_user and current_user.get("phone"):
            user_phone = current_user.get("phone")
        else:
            db_user = db.get_document("users", customer_id)
            if db_user and db_user.get("phone"):
                user_phone = db_user.get("phone")

    user_name = user_name or "Customer"
    user_phone = user_phone or ""

    # Keep users collection updated with customer details
    existing_user = db.get_document("users", customer_id) or {}
    db.set_document("users", customer_id, {
        **existing_user,
        "uid": customer_id,
        "role": "customer",
        "name": user_name,
        "phone": user_phone,
    })

    doc_data = {
        "id": job_id,
        "customerId": customer_id,
        "customerName": user_name,
        "customerPhone": user_phone,
        "category": job_data.category.lower().strip(),
        "description": job_data.description,
        "location": job_data.location.model_dump(),
        "budget": job_data.budget,
        "mode": job_data.mode or "on-demand",
        "scheduledAt": job_data.scheduledAt,
        "status": "open",
        "acceptedWorkerId": None,
        "finalPrice": None,
        "createdAt": now_iso
    }

    db.set_document("jobs", job_id, doc_data)
    return doc_data


def get_job(job_id: str, requester: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    job = db.get_document("jobs", job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found"
        )

    response_job = dict(job)

    # Enrich customer details if missing from historical/legacy job record
    if not response_job.get("customerName") or not response_job.get("customerPhone"):
        cust_user = db.get_document("users", response_job.get("customerId", ""))
        if cust_user:
            if not response_job.get("customerName"):
                response_job["customerName"] = cust_user.get("name")
            if not response_job.get("customerPhone"):
                response_job["customerPhone"] = cust_user.get("phone")

    # Privacy Protection (PRD Section 9):
    # Exact customer address is revealed to a worker only if they are the accepted worker for an active/completed booking.
    if requester and requester.get("role") == "worker":
        worker_uid = requester.get("uid")
        if job.get("acceptedWorkerId") != worker_uid or job.get("status") not in ["accepted", "in_progress", "completed"]:
            loc = dict(response_job.get("location", {}))
            loc["address"] = "Exact address hidden until booking confirmed"
            response_job["location"] = loc

    return response_job


def get_nearby_jobs_for_worker(worker_id: str) -> List[Dict[str, Any]]:
    """
    Returns open/negotiating jobs that match the worker's skills
    and fall within the worker's service radius, sorted by distance.
    """
    worker = db.get_document("workers", worker_id)
    if not worker:
        # Fallback to general open jobs if worker profile not registered
        all_jobs = db.list_collection("jobs")
        return [
            {"job": j, "distanceKm": 0.0, "etaMinutes": 0.0}
            for j in all_jobs if j.get("status") in ["open", "negotiating"]
        ]

    worker_skills = [s.lower().strip() for s in worker.get("skills", [])]
    worker_loc = worker.get("location", {})
    w_lat = worker_loc.get("lat")
    w_lng = worker_loc.get("lng")
    service_radius = float(worker.get("serviceRadiusKm", 5.0))

    all_jobs = db.list_collection("jobs")
    nearby: List[Dict[str, Any]] = []

    for job in all_jobs:
        if job.get("status") not in ["open", "negotiating"]:
            continue

        job_cat = job.get("category", "").lower().strip()
        if worker_skills and job_cat not in worker_skills:
            continue

        job_loc = job.get("location", {})
        j_lat = job_loc.get("lat")
        j_lng = job_loc.get("lng")
        if j_lat is None or j_lng is None:
            continue

        if w_lat is not None and w_lng is not None:
            dist_km = haversine_distance(w_lat, w_lng, j_lat, j_lng)
            if dist_km > service_radius:
                continue
            eta_min = calculate_eta(dist_km)
        else:
            dist_km = 0.0
            eta_min = 0.0

        # Privacy address mask for feed
        feed_job = dict(job)
        loc_copy = dict(feed_job.get("location", {}))
        loc_copy["address"] = "Exact address hidden until booking confirmed"
        feed_job["location"] = loc_copy

        nearby.append({
            "job": feed_job,
            "distanceKm": round(dist_km, 2),
            "etaMinutes": round(eta_min, 1)
        })

    nearby.sort(key=lambda x: x["distanceKm"])
    return nearby


def start_job(job_id: str, worker_id: str) -> Dict[str, Any]:
    job = db.get_document("jobs", job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found"
        )

    current_status = job.get("status")
    if current_status != "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start job: job status is '{current_status}', expected 'accepted'"
        )

    accepted_worker = job.get("acceptedWorkerId")
    if accepted_worker and accepted_worker != worker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned accepted worker can start this job"
        )

    updated = db.update_document("jobs", job_id, {
        "status": "in_progress",
        "startedAt": datetime.now(timezone.utc).isoformat()
    })
    return updated


def complete_job(job_id: str, worker_id: str) -> Dict[str, Any]:
    job = db.get_document("jobs", job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found"
        )

    current_status = job.get("status")
    if current_status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete job: job status is '{current_status}', expected 'in_progress'"
        )

    accepted_worker = job.get("acceptedWorkerId")
    if accepted_worker and accepted_worker != worker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned worker can complete this job"
        )

    updated = db.update_document("jobs", job_id, {
        "status": "completed",
        "completedAt": datetime.now(timezone.utc).isoformat()
    })

    # Increment jobsDone count for the worker
    if accepted_worker:
        worker = db.get_document("workers", accepted_worker)
        if worker:
            current_done = int(worker.get("jobsDone", 0))
            db.update_document("workers", accepted_worker, {
                "jobsDone": current_done + 1
            })

    return updated



def cancel_job(job_id: str, caller_uid: str, caller_role: str) -> Dict[str, Any]:
    with db._lock:
        job = db.get_document("jobs", job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID '{job_id}' not found"
            )

        current_status = job.get("status")
        if current_status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a job that has already been completed"
            )
        if current_status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job is already cancelled"
            )

        # Only customer of the job or admin can cancel
        if caller_role != "admin" and job.get("customerId") != caller_uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the customer who created this job or an admin can cancel it"
            )

        updated = db.update_document("jobs", job_id, {
            "status": "cancelled",
            "cancelledAt": datetime.now(timezone.utc).isoformat()
        })

        # Auto-reject any pending offers on this job
        all_job_offers = db.query_collection("offers", {"jobId": job_id})
        for off in all_job_offers:
            if off.get("status") == "pending":
                db.update_document("offers", off.get("id"), {"status": "rejected"})

        return updated


