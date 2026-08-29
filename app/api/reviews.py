"""
Review endpoints: allow a human editor to accept, reject, or otherwise
update the status of a recommended editorial decision.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.editorial_review import EditorialReview
from app.schemas.episode import EditorialReviewOut, ReviewUpdate

router = APIRouter(prefix="/api/v1/episodes", tags=["reviews"])


@router.post("/{episode_id}/reviews", response_model=EditorialReviewOut)
def update_review(
    episode_id: int, payload: ReviewUpdate, db: Session = Depends(get_db)
):
    """Update the status of a single EditorialReview belonging to this
    episode (e.g. mark a clip candidate as accepted or rejected)."""
    review = (
        db.query(EditorialReview)
        .filter(
            EditorialReview.id == payload.review_id,
            EditorialReview.episode_id == episode_id,
        )
        .first()
    )
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Review {payload.review_id} not found for episode "
                f"{episode_id}."
            ),
        )

    review.status = payload.status
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
