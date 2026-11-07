/** The clarify question card. */
export interface ClarifyCopy {
  notReady: string
  gatewayDisconnected: string
  sendFailed: string
  loadingQuestion: string
  other: string
  placeholder: string
  skip: string
  skipped: string
  noAnswer: string
  confirmAndContinueLabel: string
  /** The single-question card's submit; the batch form uses `confirmAndContinueLabel`. */
  continueLabel: string
  /** Sits beside the ✓ on a question already answered in a batch. */
  answeredBadge: string
  /** The composer text handed back when an answer lands after the card closed. */
  lateAnswer: (question: string, choice: string) => string
  lateAnswerHint: string
  lateAnswerTip: string
  singleSelectHint: string
  multiSelectHint: string
  oneQuestion: string
  questionProgress: (answered: number, total: number) => string
  notDelivered: string
}
