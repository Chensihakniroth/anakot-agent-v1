"""Host-wide gateway ownership and profile-attach helpers."""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("gateway.run")


async def _host_attach_or_none(replace: bool, force: bool = False) -> Optional[bool]:
    """Attach to the host gateway or refuse; ``None`` means this process may start."""
    from gateway.run import _start_gateway_replace_existing_instance, get_anakot_home
    from gateway.host_attach import ATTACH, REFUSE, REPLACE_HOST, decide

    if force:
        logger.warning("--force: starting a gateway without asking the host owner.")
        return None

    decision = decide(get_anakot_home(), replace=replace)
    if decision.outcome == ATTACH:
        logger.info("Attaching to the host gateway instead of starting a second one: %s",
                    decision.owner.describe() if decision.owner else "unknown")
        print(decision.message)
        return True
    if decision.outcome == REFUSE:
        logger.error("Refusing to start a second gateway on this host: %s",
                     decision.owner.describe() if decision.owner else "unknown")
        print(decision.message)
        return False
    if decision.outcome == REPLACE_HOST and decision.owner is not None:
        if not await _start_gateway_replace_existing_instance(decision.owner.pid, True):
            return False
    return None


def _claim_host_gateway_role(force: bool = False) -> None:
    """Claim the host-wide gateway lock or refuse a second multiplexer."""
    from gateway import host_rendezvous as hr
    from gateway.run import (
        _migrate_command, _owner_is_standalone, _refuse_second_host_gateway,
        get_anakot_home, logger,
    )

    home = get_anakot_home()
    if not force:
        from gateway.host_attach import REFUSE, standalone_attach_decision

        decision = standalone_attach_decision(home, None)
        if decision is not None and decision.outcome == REFUSE:
            from gateway.restart import GATEWAY_SERVICE_RESTART_EXIT_CODE

            print(decision.message)
            raise SystemExit(GATEWAY_SERVICE_RESTART_EXIT_CODE)

    try:
        outcome, error = hr.claim_host_lock(hr.ROLE_GATEWAY)
        if outcome is hr.HostLockOutcome.ACQUIRED:
            hr.publish_record(hr.ROLE_GATEWAY, profiles=(), home=str(home))
            hr.cleanup_on_exit(hr.ROLE_GATEWAY)
            return
        if outcome is hr.HostLockOutcome.COULD_NOT_OPEN:
            logger.warning(
                "Host gateway lock could not be opened (%s); this gateway is not discoverable. "
                "No second gateway is implied — the lock directory itself is unusable.",
                error,
            )
            return
    except Exception:
        logger.debug("host gateway rendezvous failed", exc_info=True)
        return

    owner = None
    try:
        owner = hr.read_record(hr.ROLE_GATEWAY, include_stale=True)
    except Exception:
        logger.debug("host gateway record unreadable", exc_info=True)
    if force:
        logger.warning("--force: starting a second gateway although %s owns this host.",
                       hr.describe(owner) if owner else "another process")
        return

    from gateway.host_attach import (
        ATTACH_CHANNEL_WAIT_S, START, host_gateway, launched_by_other_tenant,
        standalone_attach_decision,
    )
    from anakot_cli.profiles import profile_is_standalone

    if owner is not None and launched_by_other_tenant(owner.home, home):
        logger.warning(
            "Another Anakot home owns a gateway on this host (%s); starting this home's gateway beside it.",
            hr.describe(owner),
        )
        return
    if profile_is_standalone(home):
        live_owner = host_gateway(wait_for_channel=ATTACH_CHANNEL_WAIT_S)
        decision = standalone_attach_decision(home, live_owner)
        if decision is not None:
            if decision.outcome == START:
                return
            from gateway.restart import GATEWAY_SERVICE_RESTART_EXIT_CODE

            print(decision.message)
            raise SystemExit(GATEWAY_SERVICE_RESTART_EXIT_CODE)
    if _owner_is_standalone():
        logger.warning(
            "Another profile's standalone gateway owns this host (%s); starting beside it rather "
            "than retrying a race no second profile can win. Fold every profile onto one gateway "
            "with: %s",
            hr.describe(owner) if owner else "owner unknown", _migrate_command(),
        )
        return
    _refuse_second_host_gateway(owner)


def _migrate_command() -> str:
    from anakot_cli.gateway_migrate import MIGRATE_COMMAND

    return MIGRATE_COMMAND


def _owner_is_standalone() -> bool:
    """True only when the live host owner confirms it is a standalone gateway."""
    from gateway import host_attach
    from gateway.run import get_anakot_home, logger, os

    try:
        owner = host_attach.host_gateway()
        if owner is None or owner.pid == os.getpid():
            return False
        answered = host_attach.request_serve_profile(
            host_attach.profile_name_for_home(get_anakot_home()), owner=owner)
        return bool(answered is not None and answered.standalone)
    except Exception:
        logger.debug("standalone-owner probe failed; keeping the second-gateway refusal", exc_info=True)
        return False


def _refuse_second_host_gateway(owner) -> None:
    """Exit retryably so a supervisor can resolve a concurrent host-gateway start."""
    from gateway import host_rendezvous as hr
    from gateway.restart import GATEWAY_SERVICE_RESTART_EXIT_CODE
    from gateway.run import _migrate_command, logger

    who = hr.describe(owner) if owner else "owner unknown (its record is gone)"
    message = (
        f"❌ Another gateway already owns this host: {who}\n"
        "   Exactly one gateway per host serves every profile, so this process will not start a\n"
        "   second one (it would double-bind this profile's platforms).\n"
        f"   Fold every profile onto the owner:  {_migrate_command()}\n"
        "   Or stop the other gateway first, then start this one.\n"
        "   Or start one anyway (skips the host-lock check):  anakot gateway run --force\n"
        "   (--replace does not skip this check; it only replaces an owner that serves this profile.)"
    )
    logger.error("Refusing to start a second gateway on this host: %s", who)
    print(message)
    raise SystemExit(GATEWAY_SERVICE_RESTART_EXIT_CODE)


def _log_standalone_profiles_at_boot(runner) -> None:
    """Report profiles excluded from the multiplexer because they opted out."""
    try:
        if not getattr(runner.config, "multiplex_profiles", False):
            return
        from anakot_cli.profiles import profile_is_standalone, profiles_to_serve

        served = set(runner.served_profile_names())
        for name, home in profiles_to_serve(multiplex=True):
            if name != "default" and name not in served and profile_is_standalone(home):
                logger.warning(
                    "profile '%s' is standalone (gateway.standalone: true); not served by this "
                    "gateway. Fold profiles onto one gateway with: anakot gateway migrate --multiplex",
                    name,
                )
    except Exception:
        logger.warning("standalone-profile boot notice failed", exc_info=True)


def _refresh_host_gateway_record(runner) -> None:
    """Publish the actual served set after the runner has settled its profile roster."""
    from gateway import host_rendezvous as hr
    from gateway.host_attach import profile_name_for_home
    from gateway.run import get_anakot_home, logger

    try:
        if not hr.owns_host_lock(hr.ROLE_GATEWAY):
            return
        home = get_anakot_home()
        served = (tuple(runner.served_profile_names())
                  if getattr(runner.config, "multiplex_profiles", False)
                  else (profile_name_for_home(home),))
        hr.publish_record(hr.ROLE_GATEWAY, profiles=served, home=str(home))
    except Exception:
        logger.debug("host gateway record refresh failed", exc_info=True)


def _start_gateway_make_restart_signal_handler(runner):
    """Build the SIGUSR1 handler that requests a graceful service restart."""
    from gateway.run import logger

    def restart_signal_handler():
        logger.info(
            "SIGUSR1 received (systemctl reload / anakot gateway restart): performing a graceful "
            "gateway restart — drain active turns, exit, supervisor relaunches. Not an in-process "
            "config reload."
        )
        runner.request_restart(detached=False, via_service=True)

    return restart_signal_handler
