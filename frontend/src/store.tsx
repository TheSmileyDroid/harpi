import { Store } from "@tanstack/react-store";
import type { IGuild } from "./api/Api";

interface IStore {
  guild?: IGuild;
}

export const store = new Store<IStore>({
  guild: undefined,
});

export const setGuild = (guild: IGuild) => {
  store.setState((state) => {
    return {
      ...state,
      guild: guild,
    };
  });
};
