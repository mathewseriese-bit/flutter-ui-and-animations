"""
System Guardian - Central Service Orchestration and Health Monitoring

This module provides a single, reliable service orchestration system that:
1. Manages service lifecycle (start, stop, restart)
2. Monitors service health with exponential backoff
3. Prevents duplicate service launches
4. Provides a single source of truth for service status
"""

import asyncio
import logging
import os
import psutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
import aiohttp
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('guardian.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Service configuration with startup order
STARTUP_ORDER = [
    {
        'name': 'character_extraction',
        'port': 8001,
        'path': 'backend/services/character_extraction/service.py',
        'health_endpoint': '/health'
    },
    {
        'name': 'document_processor',
        'port': 8002,
        'path': 'backend/services/document_processor/service.py',
        'health_endpoint': '/health'
    },
    {
        'name': 'query_engine',
        'port': 8003,
        'path': 'backend/services/query_engine/service.py',
        'health_endpoint': '/health'
    },
    {
        'name': 'metadata_service',
        'port': 8004,
        'path': 'backend/services/metadata_service/service.py',
        'health_endpoint': '/health'
    },
    {
        'name': 'rag_service',
        'port': 8005,
        'path': 'backend/services/rag_service/service.py',
        'health_endpoint': '/health'
    }
]

class ServiceManager:
    """Manages individual service processes and their state"""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.services: Dict[str, Dict] = {}
        self.venv_python = self._find_venv_python()
        
    def _find_venv_python(self) -> str:
        """Locate the virtual environment Python executable"""
        venv_paths = [
            self.root_path / '.venv' / 'Scripts' / 'python.exe',  # Windows
            self.root_path / '.venv' / 'bin' / 'python',  # Unix
            self.root_path / 'venv' / 'Scripts' / 'python.exe',
            self.root_path / 'venv' / 'bin' / 'python',
        ]
        
        for venv_path in venv_paths:
            if venv_path.exists():
                logger.info(f"Found Python at: {venv_path}")
                return str(venv_path)
        
        logger.warning("Virtual environment not found, using system Python")
        return sys.executable
    
    def is_port_in_use(self, port: int) -> Optional[int]:
        """Check if a port is in use and return the PID if it is"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == 'LISTEN':
                return conn.pid
        return None
    
    def is_service_running(self, service_name: str) -> bool:
        """Check if a service is running based on tracked PID"""
        if service_name not in self.services:
            return False
        
        service_info = self.services[service_name]
        pid = service_info.get('pid')
        
        if not pid:
            return False
        
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    async def start_service(self, config: Dict) -> bool:
        """Start a service if it's not already running"""
        service_name = config['name']
        port = config['port']
        
        # Check if port is already in use
        existing_pid = self.is_port_in_use(port)
        if existing_pid:
            logger.warning(
                f"Port {port} already in use by PID {existing_pid}. "
                f"Skipping start of {service_name}"
            )
            # Track this existing process
            self.services[service_name] = {
                'pid': existing_pid,
                'port': port,
                'started_by': 'external',
                'start_time': datetime.now()
            }
            return True
        
        # Check if we're already tracking this service
        if self.is_service_running(service_name):
            logger.info(f"{service_name} is already running")
            return True
        
        # Start the service
        service_path = self.root_path / config['path']
        if not service_path.exists():
            logger.error(f"Service script not found: {service_path}")
            return False
        
        try:
            logger.info(f"Starting {service_name} on port {port}...")
            
            # Start service as subprocess
            process = subprocess.Popen(
                [self.venv_python, str(service_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.root_path),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
            
            # Track the service
            self.services[service_name] = {
                'pid': process.pid,
                'port': port,
                'process': process,
                'started_by': 'guardian',
                'start_time': datetime.now(),
                'restart_count': 0,
                'last_restart': None
            }
            
            logger.info(f"{service_name} started with PID {process.pid}")
            
            # Wait a moment for service to bind to port
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {e}")
            return False
    
    async def stop_service(self, service_name: str) -> bool:
        """Stop a service gracefully"""
        if service_name not in self.services:
            logger.warning(f"{service_name} is not tracked by Guardian")
            return False
        
        service_info = self.services[service_name]
        pid = service_info.get('pid')
        
        if not pid:
            return False
        
        try:
            process = psutil.Process(pid)
            
            # Try graceful shutdown first
            logger.info(f"Stopping {service_name} (PID {pid})...")
            process.terminate()
            
            # Wait for process to exit
            try:
                process.wait(timeout=10)
                logger.info(f"{service_name} stopped gracefully")
            except psutil.TimeoutExpired:
                # Force kill if necessary
                logger.warning(f"Force killing {service_name}")
                process.kill()
                process.wait(timeout=5)
            
            # Remove from tracking
            del self.services[service_name]
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"Failed to stop {service_name}: {e}")
            return False
    
    def get_service_status(self) -> Dict:
        """Get status of all tracked services"""
        status = {}
        for service_name, info in self.services.items():
            is_running = self.is_service_running(service_name)
            status[service_name] = {
                'running': is_running,
                'pid': info.get('pid'),
                'port': info.get('port'),
                'started_by': info.get('started_by'),
                'start_time': info.get('start_time').isoformat() if info.get('start_time') else None,
                'restart_count': info.get('restart_count', 0)
            }
        return status


class HealthMonitor:
    """Monitors service health and handles recovery"""
    
    def __init__(self, service_manager: ServiceManager):
        self.service_manager = service_manager
        self.health_status: Dict[str, Dict] = {}
        self.backoff_delays: Dict[str, float] = {}
        self.max_backoff = 300  # 5 minutes
        self.base_backoff = 5   # 5 seconds
        
    async def check_health(self, config: Dict) -> bool:
        """Check if a service is healthy via HTTP health endpoint"""
        service_name = config['name']
        port = config['port']
        health_endpoint = config.get('health_endpoint', '/health')
        
        url = f"http://localhost:{port}{health_endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        is_healthy = data.get('status') == 'healthy'
                        
                        if is_healthy:
                            # Reset backoff on successful health check
                            self.backoff_delays[service_name] = self.base_backoff
                            
                        self.health_status[service_name] = {
                            'healthy': is_healthy,
                            'last_check': datetime.now(),
                            'response': data
                        }
                        
                        return is_healthy
        except Exception as e:
            logger.debug(f"Health check failed for {service_name}: {e}")
            self.health_status[service_name] = {
                'healthy': False,
                'last_check': datetime.now(),
                'error': str(e)
            }
            return False
    
    def get_backoff_delay(self, service_name: str) -> float:
        """Get the current backoff delay for a service"""
        if service_name not in self.backoff_delays:
            self.backoff_delays[service_name] = self.base_backoff
        return self.backoff_delays[service_name]
    
    def increase_backoff(self, service_name: str):
        """Increase backoff delay with exponential backoff"""
        current = self.backoff_delays.get(service_name, self.base_backoff)
        new_delay = min(current * 2, self.max_backoff)
        self.backoff_delays[service_name] = new_delay
        logger.info(f"Increased backoff for {service_name} to {new_delay}s")
    
    async def restart_service(self, config: Dict) -> bool:
        """Restart a service with backoff"""
        service_name = config['name']
        
        # Apply backoff delay
        delay = self.get_backoff_delay(service_name)
        logger.info(f"Waiting {delay}s before restarting {service_name}")
        await asyncio.sleep(delay)
        
        # Stop existing process if any
        await self.service_manager.stop_service(service_name)
        
        # Start the service
        success = await self.service_manager.start_service(config)
        
        if success:
            # Increase backoff for next potential restart
            self.increase_backoff(service_name)
            
            # Update restart count
            if service_name in self.service_manager.services:
                info = self.service_manager.services[service_name]
                info['restart_count'] = info.get('restart_count', 0) + 1
                info['last_restart'] = datetime.now()
        
        return success


async def background_monitor(service_manager: ServiceManager, health_monitor: HealthMonitor):
    """Background task to monitor service health and perform recovery"""
    logger.info("Starting background health monitoring...")
    
    # Initial health check delay
    await asyncio.sleep(10)
    
    while True:
        try:
            for config in STARTUP_ORDER:
                service_name = config['name']
                
                # Check if service is running
                is_running = service_manager.is_service_running(service_name)
                
                if not is_running:
                    logger.warning(f"{service_name} is not running")
                    # Try to restart
                    await health_monitor.restart_service(config)
                    continue
                
                # Check health endpoint
                is_healthy = await health_monitor.check_health(config)
                
                if not is_healthy:
                    logger.warning(f"{service_name} failed health check")
                    # Try to restart
                    await health_monitor.restart_service(config)
                else:
                    logger.debug(f"{service_name} is healthy")
            
            # Wait before next check cycle
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in background monitor: {e}")
            await asyncio.sleep(10)


async def start_all_services(service_manager: ServiceManager):
    """Start all services in the defined order"""
    logger.info("=" * 60)
    logger.info("Starting all services in order...")
    logger.info("=" * 60)
    
    for config in STARTUP_ORDER:
        success = await service_manager.start_service(config)
        if not success:
            logger.error(f"Failed to start {config['name']}")
        
        # Wait between service starts to avoid resource contention
        await asyncio.sleep(3)
    
    logger.info("=" * 60)
    logger.info("All services started")
    logger.info("=" * 60)


async def stop_all_services(service_manager: ServiceManager):
    """Stop all services gracefully"""
    logger.info("Stopping all services...")
    
    # Stop in reverse order
    for config in reversed(STARTUP_ORDER):
        service_name = config['name']
        await service_manager.stop_service(service_name)
    
    logger.info("All services stopped")


async def main():
    """Main Guardian orchestration loop"""
    # Determine root path (Auralis_App directory)
    current_file = Path(__file__).resolve()
    root_path = current_file.parent.parent.parent.parent
    
    logger.info(f"Guardian starting at: {root_path}")
    
    # Initialize managers
    service_manager = ServiceManager(root_path)
    health_monitor = HealthMonitor(service_manager)
    
    # Start all services
    await start_all_services(service_manager)
    
    # Start background monitoring
    monitor_task = asyncio.create_task(
        background_monitor(service_manager, health_monitor)
    )
    
    try:
        # Run the Guardian API server (simplified for now)
        logger.info("Guardian is running. Press Ctrl+C to stop.")
        
        # Keep Guardian alive
        await monitor_task
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested...")
        monitor_task.cancel()
        await stop_all_services(service_manager)
        logger.info("Guardian shutdown complete")
    except Exception as e:
        logger.error(f"Guardian error: {e}")
        await stop_all_services(service_manager)


if __name__ == '__main__':
    asyncio.run(main())
