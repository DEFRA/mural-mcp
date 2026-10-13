import fastapi
import pydantic
from dishka.integrations import fastapi as dishka_fastapi
from pydantic.alias_generators import to_camel

from app import config as app_config
from app.auth import principal as principal_module
from app.infra.rest.auth import dependencies as auth_deps
from app.integration.mural import access_request_service, exceptions
from app.integration.mural import models as access_request_models

router = fastapi.APIRouter()


class DecisionPayload(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(alias_generator=to_camel, populate_by_name=True)

    decision_reason: str


class ApprovalPayload(DecisionPayload):
    # Required only when DATA_HANDLING_UPLOAD_ENABLED; ignored otherwise.
    data_handling_form_ref: str | None = None
    risk_assessment_ref: str | None = None


@router.get("/access-requests")
@dishka_fastapi.inject
async def list_pending_access_requests(
    _reviewer: principal_module.Principal = fastapi.Depends(auth_deps.get_principal),
    service: dishka_fastapi.FromDishka[
        access_request_service.BoardAccessRequestService
    ] = ...,  # type: ignore[assignment]
) -> list[access_request_models.BoardAccessRequest]:
    """List board access requests awaiting IAO review.

    Reachable only by the portal — the IAO reviews and decides through the
    portal, which calls these endpoints on their behalf.
    """
    return await service.list_pending()


@router.post("/access-requests/{request_id}/approve")
@dishka_fastapi.inject
async def approve_access_request(
    request_id: str,
    payload: ApprovalPayload,
    reviewer: principal_module.Principal = fastapi.Depends(auth_deps.get_principal),
    service: dishka_fastapi.FromDishka[
        access_request_service.BoardAccessRequestService
    ] = ...,  # type: ignore[assignment]
    config: dishka_fastapi.FromDishka[app_config.AppConfig] = ...,  # type: ignore[assignment]
) -> access_request_models.BoardAccessRequest:
    """Approve a pending access request, recording the IAO's decision reason.

    With DATA_HANDLING_UPLOAD_ENABLED the approval must also reference the
    data-handling form and risk assessment; without it those are not
    collected and any supplied references are discarded."""
    form_ref = risk_ref = None
    if config.data_handling_upload_enabled:
        if not (payload.data_handling_form_ref and payload.risk_assessment_ref):
            raise fastapi.HTTPException(
                status_code=422,
                detail="dataHandlingFormRef and riskAssessmentRef are required.",
            )
        form_ref = payload.data_handling_form_ref
        risk_ref = payload.risk_assessment_ref

    try:
        return await service.approve(
            request_id,
            reviewer.user_id,
            payload.decision_reason,
            form_ref,
            risk_ref,
        )
    except exceptions.AccessRequestNotFoundError as exc:
        raise fastapi.HTTPException(status_code=404, detail=str(exc)) from exc
    except exceptions.AccessRequestAlreadyDecidedError as exc:
        raise fastapi.HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/access-requests/{request_id}/reject")
@dishka_fastapi.inject
async def reject_access_request(
    request_id: str,
    payload: DecisionPayload,
    reviewer: principal_module.Principal = fastapi.Depends(auth_deps.get_principal),
    service: dishka_fastapi.FromDishka[
        access_request_service.BoardAccessRequestService
    ] = ...,  # type: ignore[assignment]
) -> access_request_models.BoardAccessRequest:
    """Reject a pending access request, recording the IAO's decision reason."""
    try:
        return await service.reject(
            request_id, reviewer.user_id, payload.decision_reason
        )
    except exceptions.AccessRequestNotFoundError as exc:
        raise fastapi.HTTPException(status_code=404, detail=str(exc)) from exc
    except exceptions.AccessRequestAlreadyDecidedError as exc:
        raise fastapi.HTTPException(status_code=409, detail=str(exc)) from exc
