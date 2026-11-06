# shellcheck shell=sh
# Installed as /etc/profile.d/anakot.sh. Debian's /etc/profile resets PATH for
# every login shell (`bash -l`, `docker exec <c> bash -l`, ssh, the terminal
# tool's background `bash -lic`), dropping the image's ENV PATH dirs, so bare
# `anakot` exits 127 there. Put them back in the ENV PATH order; dirs a login
# PATH already lists keep their position.
for __anakot_p in /opt/data/.local/bin /opt/anakot/.venv/bin /opt/anakot/bin; do
    case ":$PATH:" in
        *":$__anakot_p:"*) ;;
        *) PATH="$__anakot_p:$PATH" ;;
    esac
done
unset __anakot_p
export PATH
