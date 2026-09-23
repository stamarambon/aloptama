import { supabase } from '../supabaseClient';

const BUCKET_NAME = 'aloptama-images';

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

export async function emptyImageBucket() {
  try {
    let deleted = 0;

    while (true) {
      const { data, error } = await supabase.storage.from(BUCKET_NAME).list('', {
        limit: 1000,
        offset: 0,
      });

      if (error) {
        throw error;
      }

      const files = (data || []).filter((item) => item?.name && item.id);
      if (files.length === 0) {
        break;
      }

      const paths = files.map((item) => item.name);
      const { error: removeError } = await supabase.storage.from(BUCKET_NAME).remove(paths);
      if (removeError) {
        throw removeError;
      }

      deleted += paths.length;
      if (files.length < 1000) {
        break;
      }
    }

    const { error: dbError } = await supabase
      .from('aloptama')
      .update({ gambar_url: null })
      .not('id', 'is', null);

    if (dbError) {
      throw dbError;
    }

    return { deleted, error: null };
  } catch (error) {
    console.error('Error emptying bucket:', error);
    return { deleted: 0, error: error.message || String(error) };
  }
}
