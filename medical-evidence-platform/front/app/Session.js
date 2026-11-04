'use client';
import {createContext,useContext,useState} from 'react';
const Context=createContext(null);
export function SessionProvider({children}){const [token,setToken]=useState(''),[patients,setPatients]=useState([]),[patient,setPatient]=useState(''),[encounter,setEncounter]=useState(''),[connected,setConnected]=useState(false),[unsaved,setUnsaved]=useState(false);return <Context.Provider value={{token,setToken,patients,setPatients,patient,setPatient,encounter,setEncounter,connected,setConnected,unsaved,setUnsaved}}>{children}</Context.Provider>}
export const useSession=()=>useContext(Context);
