// ABOUTME: Barrel for the chat's state and mappers between the backend's chat bodies and the UI's shapes.
// ABOUTME: Import from "@/lib/chat" rather than reaching into individual files.

export { chatReducer, hasStarted, initialChatState, type ChatAction, type ChatState, type PendingSend } from './chat-reducer';
export { FALLBACK_RESOURCES, helpLines, siteName, type HelpLines } from './help-lines';
export {
  emergencyLeads,
  isPauseActive,
  opensCrisisScreen,
  pauseFromError,
  pauseIn,
  pauseLength,
  type ChatPause,
  type PauseUnit,
} from './pause';
export { errorText, messageFromTurn, messageFromWire, messagesFromWire, threadFromWire } from './to-ui';
