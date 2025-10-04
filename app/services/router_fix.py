"""
修复后的 route_streaming_request 方法
复制这段代码替换 router.py 中的对应方法
"""

async def route_streaming_request(
    self,
    provider_name: str,
    request: ChatCompletionRequest,
    request_id: str,
    api_key: Optional[str] = None,
    client_ip: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Route streaming request to provider with Token usage tracking.
    
    CRITICAL FIX: Uses finally block to ensure logging happens after generator completes.
    
    Args:
        provider_name: Target provider name
        request: Chat completion request
        request_id: Unique request ID
        api_key: User API key
        client_ip: Client IP address
        
    Yields:
        Server-sent event chunks
    """
    start_time = time.time()
    
    # Get provider
    provider = await self._get_provider(provider_name)
    if not provider:
        raise Exception(f"Provider {provider_name} not found")
    
    # Track usage info and stream state
    usage_info: Optional[Dict[str, Any]] = None
    last_chunk: Optional[str] = None
    stream_error: Optional[Exception] = None
    
    try:
        # Create provider instance
        provider_instance = self.provider_factory.create_provider(
            provider_type=provider.type,
            api_key=provider.api_key,
            base_url=provider.base_url,
            timeout=request.timeout or provider.timeout
        )
        
        # Stream response and track last chunk
        try:
            async for chunk in provider_instance.chat_completion_stream(request):
                # Track the last valid chunk (not [DONE])
                if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                    last_chunk = chunk
                
                yield chunk
        except Exception as e:
            stream_error = e
            raise
    
    except Exception as e:
        stream_error = e
        logger.error(
            f"Streaming request failed on {provider_name}: {str(e)}",
            extra={
                "request_id": request_id,
                "provider": provider_name,
                "error": str(e)
            }
        )
        
        # Log failed request
        latency_ms = int((time.time() - start_time) * 1000)
        await self._log_failed_request(
            provider_id=provider.id,
            request=request,
            error=str(e),
            latency_ms=latency_ms,
            api_key=api_key,
            client_ip=client_ip
        )
        
        raise
    
    finally:
        # CRITICAL: This block ALWAYS executes after generator completes
        if not stream_error:
            # Extract usage from last chunk
            if last_chunk:
                try:
                    data_str = last_chunk[6:].strip()
                    data = json.loads(data_str)
                    
                    if "usage" in data:
                        usage = data["usage"]
                        if usage.get("total_tokens", 0) > 0:
                            usage_info = usage
                            logger.debug(
                                "Extracted usage from last chunk",
                                extra={
                                    "prompt_tokens": usage.get("prompt_tokens"),
                                    "completion_tokens": usage.get("completion_tokens"),
                                    "total_tokens": usage.get("total_tokens")
                                }
                            )
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to extract usage: {str(e)}")
            
            # Log successful streaming request
            latency_ms = int((time.time() - start_time) * 1000)
            await self._log_streaming_request(
                provider_id=provider.id,
                request=request,
                usage_info=usage_info,
                latency_ms=latency_ms,
                api_key=api_key,
                client_ip=client_ip
            )
            
            logger.info(
                "Streaming completed successfully",
                extra={
                    "request_id": request_id,
                    "provider": provider_name,
                    "has_usage": usage_info is not None,
                    "total_tokens": usage_info.get("total_tokens") if usage_info else 0
                }
            )