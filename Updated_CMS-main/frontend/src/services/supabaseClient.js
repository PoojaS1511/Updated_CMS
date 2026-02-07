// This file re-exports the main Supabase client instance from supabaseConfig
// to maintain backward compatibility with existing imports
import { supabase, TABLES } from './supabaseConfig';

export { supabase, TABLES };
export default supabase;
