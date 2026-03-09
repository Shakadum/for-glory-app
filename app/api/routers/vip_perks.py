"""
ForGlory — VIP Perks
Lógica de desbloqueio: borda prata/ouro, cor do nome.

Regras:
  Prata: ativa quando assinatura ativa, bloqueia ao cancelar
  Ouro:  desbloqueia na assinatura anual OU após 12 meses acumulados
         flag permanente: uma vez desbloqueado, basta reativar a assinatura
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.core import get_db, get_current_active_user
from app.models.models import User
from app.models.features import Subscription, VipPerk

router = APIRouter()


def _utcnow():
    return datetime.now(timezone.utc)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_or_create_perk(db: Session, user_id: int) -> VipPerk:
    perk = db.query(VipPerk).filter_by(user_id=user_id).first()
    if not perk:
        perk = VipPerk(user_id=user_id)
        db.add(perk)
        db.commit()
        db.refresh(perk)
    return perk


def has_active_vip(user: User, db: Session) -> bool:
    sub = db.query(Subscription).filter_by(user_id=user.id, status='active').first()
    return sub is not None


def is_annual_plan(user: User, db: Session) -> bool:
    sub = db.query(Subscription).filter_by(user_id=user.id, status='active').first()
    if not sub or not sub.plan:
        return False
    return sub.plan.slug in ('vip_anual', 'vip_annual', 'anual', 'annual')


def compute_vip_status(user: User, db: Session) -> dict:
    """
    Retorna status completo das perks VIP do usuário.
    Chamado no /me e no painel VIP.
    """
    active = has_active_vip(user, db)
    perk   = get_or_create_perk(db, user.id)

    # Prata: só disponível se assinatura ativa
    silver_available = active

    # Ouro: disponível se (a) assinatura ativa E (b) já desbloqueou antes OU 12 meses OU anual
    gold_unlocked = bool(perk.gold_border_unlocked)
    gold_available = active and gold_unlocked

    # Checar se deve desbloquear ouro agora
    if active and not gold_unlocked:
        if is_annual_plan(user, db):
            perk.gold_border_unlocked = 1
            perk.annual_sub_unlocked  = 1
            perk.gold_border_unlocked_at = _utcnow()
            db.commit()
            gold_unlocked = True
            gold_available = True
        elif perk.total_vip_months >= 12:
            perk.gold_border_unlocked = 1
            perk.gold_border_unlocked_at = _utcnow()
            db.commit()
            gold_unlocked = True
            gold_available = True

    # Borda atual efetiva (bloquear se assinatura inativa)
    current_border = getattr(user, 'vip_border', 'none') or 'none'
    if current_border == 'prata' and not silver_available:
        current_border = 'none'
    if current_border == 'ouro' and not gold_available:
        current_border = 'none'

    return {
        "is_vip": active,
        "silver_available": silver_available,
        "gold_available": gold_available,
        "gold_unlocked_permanently": gold_unlocked,
        "gold_unlocked_at": perk.gold_border_unlocked_at.isoformat() if perk.gold_border_unlocked_at else None,
        "total_vip_months": perk.total_vip_months,
        "months_to_gold": max(0, 12 - perk.total_vip_months),
        "current_border": current_border,
        "name_color": getattr(user, 'vip_name_color', None),
        # Url das imagens
        "borders": {
            "prata": "/static/vip_border_prata.jpg" if silver_available else None,
            "ouro":  "/static/vip_border_ouro.jpg"  if gold_available   else None,
        },
        "bubble_ouro": "/static/vip_bubble_ouro.jpg" if gold_available else None,
    }


def increment_vip_month(user_id: int, db: Session):
    """Chamado mensalmente pelo webhook de pagamento confirmado."""
    perk = get_or_create_perk(db, user_id)
    perk.total_vip_months += 1
    perk.updated_at = _utcnow()
    db.commit()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/my/vip-perks")
def get_vip_perks(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Status completo das perks VIP do usuário logado."""
    return compute_vip_status(user, db)


@router.post("/my/vip-perks/set-border")
def set_vip_border(
    data: dict = Body(...),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Define a borda ativa. Valida se o usuário tem direito."""
    border = str(data.get("border", "none")).lower()
    if border not in ("none", "prata", "ouro"):
        return {"error": "Borda inválida"}

    status = compute_vip_status(user, db)

    if border == "prata" and not status["silver_available"]:
        return {"error": "Borda Prata requer assinatura VIP ativa"}
    if border == "ouro" and not status["gold_available"]:
        return {"error": "Borda Ouro ainda não desbloqueada"}

    user.vip_border = border
    db.commit()
    return {"status": "ok", "border": border}


@router.post("/my/vip-perks/set-name-color")
def set_name_color(
    data: dict = Body(...),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Define cor customizada do nome (só VIP)."""
    status = compute_vip_status(user, db)
    if not status["is_vip"]:
        return {"error": "Requer assinatura VIP ativa"}

    color = str(data.get("color", "")).strip()
    # Validar hex simples
    import re
    if color and not re.match(r'^#[0-9a-fA-F]{3,6}$', color):
        return {"error": "Cor inválida. Use formato #RRGGBB"}

    user.vip_name_color = color or None
    db.commit()
    return {"status": "ok", "color": color}
