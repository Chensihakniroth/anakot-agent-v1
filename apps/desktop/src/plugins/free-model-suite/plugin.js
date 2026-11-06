import { jsx as _jsx } from "react/jsx-runtime";
import { host, PALETTE_AREA, ROUTES_AREA, SIDEBAR_NAV_AREA } from '@anakot/plugin-sdk';
import { bindApi } from './api';
import { FREE_MODEL_SUITE_LOCALES } from './i18n';
import { FreeModelSuitePage } from './page';
const plugin = {
    id: 'free-model-suite',
    name: 'Free Model Suite',
    description: 'Browse, probe, and apply free models from providers already connected to this profile.',
    defaultEnabled: true,
    register(ctx) {
        ctx.i18n.register(FREE_MODEL_SUITE_LOCALES);
        ctx.onDispose(bindApi(ctx.rest));
        ctx.registerMany([
            {
                id: 'page',
                area: ROUTES_AREA,
                title: 'Free Model Suite',
                data: { path: '/free-models' },
                render: () => _jsx(FreeModelSuitePage, {})
            },
            {
                id: 'nav',
                area: SIDEBAR_NAV_AREA,
                order: 45,
                data: { codicon: 'leaf', label: 'Free Models', path: '/free-models' }
            },
            {
                id: 'open',
                area: PALETTE_AREA,
                data: {
                    id: 'free-model-suite.open',
                    keywords: ['free', 'models', 'provider', 'cheap', 'zero cost'],
                    label: 'Free Models: Open',
                    run: () => host.navigate('/free-models')
                }
            }
        ]);
    }
};
export default plugin;
