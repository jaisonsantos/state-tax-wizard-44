-- Deletes processed webhooks older than 30 days that are not in DLQ
DELETE FROM processed_webhooks
 WHERE status = 'processed'
   AND dead_letter = false
   AND processed_at < NOW() - INTERVAL '30 days';
