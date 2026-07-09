import type { GameState, LogEntry, SaveActionResult, SaveSlotInfo, Verb } from "../types/game";
import type { TransitionVisualState } from "./transitions";

export type AppView = "start" | "load" | "intro" | "game" | "cinematic" | "introStory";

export interface GameStore {
  view: AppView;
  game: GameState | null;
  logs: LogEntry[];
  loading: boolean;
  error: string | null;
  selectedVerb: Verb | null;
  selectedTarget: string | null;
  codeInput: string;
  transition: TransitionVisualState;
  viewTransition: TransitionVisualState;
  dirty: boolean;
  saveSlots: SaveSlotInfo[] | null;
  slotsLoading: boolean;
  savingSlot: number | null;
  loadingSlot: number | null;
  exitConfirmOpen: boolean;
  examineImage: string | null;
  cinematicTitle: string;
  cinematicSubtitle: string;
  introVisibleLines: string[];
  introFadeOutMs: number;
  introRunId: number;
  isSpectator: boolean;

  setView: (view: AppView) => void;
  cancelRemember: () => void;
  startNewGame: () => Promise<void>;
  executeCommand: (command: string) => Promise<void>;
  setSelectedVerb: (verb: Verb | null) => void;
  setSelectedTarget: (target: string | null) => void;
  setCodeInput: (code: string) => void;
  clearSelection: () => void;
  runTransition: (options: import("./transitions").TransitionOptions) => Promise<void>;
  runViewTransition: (options: import("./transitions").TransitionOptions) => Promise<void>;
  startExploreSequence: () => Promise<void>;
  playEndingSequence: () => Promise<void>;
  startIntroSequence: () => Promise<void>;
  skipIntro: () => void;
  attachSpectate: (sessionId: string) => Promise<void>;
  detachSpectate: () => void;
  fetchSaveSlots: () => Promise<void>;
  saveToSlot: (slot: number) => Promise<SaveActionResult>;
  loadFromSlot: (slot: number) => Promise<void>;
  requestExit: () => void;
  confirmExit: () => void;
  cancelExit: () => void;
  closeExamineImage: () => void;
}

export type GameStoreSet = (
  partial: Partial<GameStore> | ((state: GameStore) => Partial<GameStore>),
) => void;
export type GameStoreGet = () => GameStore;
