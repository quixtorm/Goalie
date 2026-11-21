import { createContext, useContext } from 'react'

// One shared app context: state, navigation, language, hide-amounts, and openers for the sheets.
export const AppCtx = createContext(null)
export const useApp = () => useContext(AppCtx)
