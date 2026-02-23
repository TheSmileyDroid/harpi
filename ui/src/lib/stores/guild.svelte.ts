import { browser } from '$app/environment';
import type { GuildResponse, ChannelsResponse } from '$lib/api/models';

export type { GuildResponse, ChannelsResponse };

const STORAGE_KEY = 'harpi_selected_guild';

function createGuildStore() {
	let selectedGuild = $state<GuildResponse | null>(null);

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
		select(guild: GuildResponse | null) {
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
