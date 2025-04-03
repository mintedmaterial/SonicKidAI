/**
 * API keys management route for SonicKid AI
 * Handles checking and requesting API keys for external services
 */

import { Router } from 'express';
import { db } from '../db';
import { apiKeys } from '@shared/schema';
import { eq } from 'drizzle-orm';

const router = Router();

// Get all service names (not the keys for security)
router.get('/', async (req, res) => {
  try {
    console.log('Fetching API key services...');
    const services = await db.select({
      serviceName: apiKeys.serviceName,
      isActive: apiKeys.isActive,
      createdAt: apiKeys.createdAt
    }).from(apiKeys);
    
    console.log(`Found ${services.length} API service integrations`);
    res.json(services);
  } catch (error) {
    console.error('Error fetching API keys:', error);
    res.status(500).json({ error: 'Failed to fetch API keys' });
  }
});

// Check if a specific service has an API key
router.get('/:service/check', async (req, res) => {
  try {
    const { service } = req.params;
    console.log(`Checking if API key exists for ${service}...`);
    
    // Simplify by just checking if any records exist
    const records = await db.select()
      .from(apiKeys)
      .where(eq(apiKeys.serviceName, service));
    
    const keyExists = records.length > 0;
    console.log(`API key for ${service} exists: ${keyExists}`);
    
    res.json({ 
      service,
      exists: keyExists
    });
  } catch (error) {
    console.error(`Error checking API key for ${req.params.service}:`, error);
    res.status(500).json({ error: 'Failed to check API key status' });
  }
});

// Add or update API key for a service
router.post('/:service', async (req, res) => {
  try {
    const { service } = req.params;
    const { apiKey } = req.body;
    
    if (!apiKey) {
      return res.status(400).json({ error: 'API key is required' });
    }
    
    console.log(`Saving API key for ${service}...`);
    
    // Check if service already exists
    const existing = await db.select({
      id: apiKeys.id
    })
    .from(apiKeys)
    .where(eq(apiKeys.serviceName, service));
    
    if (existing.length > 0) {
      // Update existing record
      await db.update(apiKeys)
        .set({ 
          apiKey,
          isActive: true,
          updatedAt: new Date()
        })
        .where(eq(apiKeys.serviceName, service));
      
      console.log(`Updated API key for ${service}`);
    } else {
      // Insert new record
      await db.insert(apiKeys).values({
        serviceName: service,
        apiKey,
        isActive: true,
        metadata: {}
      });
      
      console.log(`Added new API key for ${service}`);
    }
    
    res.json({ 
      success: true, 
      message: `API key for ${service} saved successfully`
    });
  } catch (error) {
    console.error(`Error saving API key for ${req.params.service}:`, error);
    res.status(500).json({ error: 'Failed to save API key' });
  }
});

// Delete API key for a service
router.delete('/:service', async (req, res) => {
  try {
    const { service } = req.params;
    console.log(`Deleting API key for ${service}...`);
    
    await db.delete(apiKeys)
      .where(eq(apiKeys.serviceName, service));
    
    console.log(`Deleted API key for ${service}`);
    res.json({ 
      success: true, 
      message: `API key for ${service} deleted successfully`
    });
  } catch (error) {
    console.error(`Error deleting API key for ${req.params.service}:`, error);
    res.status(500).json({ error: 'Failed to delete API key' });
  }
});

// Internal route to get API key value by service name
router.get('/:service/key', async (req, res) => {
  try {
    const { service } = req.params;
    
    // This route should only be accessible from the server itself
    const requestIp = req.ip;
    if (requestIp !== '127.0.0.1' && requestIp !== '::1' && requestIp !== '::ffff:127.0.0.1') {
      console.warn(`Unauthorized access attempt to API key from ${requestIp}`);
      return res.status(403).json({ error: 'Access denied' });
    }
    
    console.log(`Getting API key for ${service}...`);
    
    const key = await db.select({
      apiKey: apiKeys.apiKey,
      isActive: apiKeys.isActive
    })
    .from(apiKeys)
    .where(eq(apiKeys.serviceName, service));
    
    if (key.length === 0 || !key[0].isActive) {
      return res.status(404).json({ error: `No active API key found for ${service}` });
    }
    
    res.json({ apiKey: key[0].apiKey });
  } catch (error) {
    console.error(`Error retrieving API key for ${req.params.service}:`, error);
    res.status(500).json({ error: 'Failed to retrieve API key' });
  }
});

export default router;