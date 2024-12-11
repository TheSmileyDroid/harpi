import { Store } from "@tanstack/react-store";
import type { IGuild, IMusicState } from "./api/Api";

interface IStore {
  guild?: IGuild;
  musicState?: IMusicState;
}

export const store = new Store<IStore>({
  guild: undefined,
  musicState: undefined,
});

export const setGuild = (guild: IGuild) => {
  store.setState((state) => {
    return {
      ...state,
      guild: guild,
    };
  });
};

export const setMusicState = (musicState: any) => {
  store.setState((state) => {
    return {
      ...state,
      musicState: musicState,
    };
  });
};
