import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.error(
    'Supabase URL atau Anon Key belum terdeteksi!\n' +
    'Pastikan file .env ada dan server Vite telah di-restart (npm run dev).'
  )
}

export const supabase = createClient(supabaseUrl || '', supabaseAnonKey || '')

