import { browser } from '$app/environment';

const STORAGE_KEY = 'harpi_selected_guild';

export type Guild = {
    id: string;
    name: string;
    icon: string | null;
};

function createGuildStore() {
    let selectedGuild = $state<Guild | null>(null);

    if (browser) {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
            try {
                selectedGuild = JSON.parse(stored);
            } catch {
                localStorage.removeItem(STORAGE_KEY);
            }
        }
    }

    return {
        get current() {
            return selectedGuild;
        },
        select(guild: Guild | null) {
            selectedGuild = guild;
            if (browser) {
                if (guild) {
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(guild));
                } else {
                    localStorage.removeItem(STORAGE_KEY);
                }
            }
        },
        clear() {
            selectedGuild = null;
            if (browser) {
                localStorage.removeItem(STORAGE_KEY);
            }
        }
    };
}

export const guildStore = createGuildStore();
