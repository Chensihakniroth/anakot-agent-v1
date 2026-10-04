"""OmniRouters provider profile.

omnirouters.com fronts ~160 upstream models behind one OpenAI-compatible
gateway: Bearer auth, ``/v1/chat/completions``, ``/v1/models``, plus
Responses/Claude/Gemini-native aliases. Only the OpenAI chat surface is used
here — it is the broadest and the safest default for cross-model traffic.

Two deliberate omissions:

* ``fallback_models`` is empty. The catalog is *account-scoped* (a model is
  callable only if the account has it enabled), so any hardcoded list would
  route aux/picker defaults at models this key cannot reach. ``fetch_models``
  is the source of truth.
* No reasoning fields are emitted. OmniRouters documents ``extra_body`` as a
  generic provider-extension container rather than a declared ``reasoning``
  schema, and the core gate (``_supports_reasoning_extra_body``) does not
  vouch for this host, so a blind ``extra_body.reasoning`` risks a 400 on
  routes that reject unknown keys.
"""

from providers import register_provider
from providers.base import ProviderProfile


omnirouters = ProviderProfile(
    name="omnirouters",
    aliases=("omni-router", "omnirouter", "omni"),
    display_name="OmniRouters",
    description="OmniRouters — one key for ~160 chat, image, video and audio models",
    signup_url="https://omnirouters.com/keys",
    env_vars=("OMNIROUTERS_API_KEY", "OMNIROUTERS_BASE_URL"),
    base_url="https://omnirouters.com/v1",
    auth_type="api_key",
    supports_vision=True,
    default_aux_model="",
    fallback_models=(),  # account-scoped ids; the picker uses fetch_models()
)

register_provider(omnirouters)
