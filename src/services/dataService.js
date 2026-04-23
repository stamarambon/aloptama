import { supabase } from '../supabaseClient';

export async function fetchDevices() {
  try {
    const { data, error } = await supabase
      .from('aloptama')
      .select('*')
      .order('timestamp', { ascending: false });

    if (error) {
      throw error;
    }

    return { data, error: null };
  } catch (error) {
    console.error('Error fetching devices:', error);
    return { data: null, error: error.message };
  }
}

// Optional: function to subscribe to realtime changes
export function subscribeToDevices(callback) {
  return supabase
    .channel('aloptama-changes')
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'aloptama'
      },
      (payload) => {
        callback(payload);
      }
    )
    .subscribe();
}
