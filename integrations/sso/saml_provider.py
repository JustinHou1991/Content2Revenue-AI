#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content2Revenue AI - SAML 2.0 SSO 集成
支持企业级单点登录 (Okta, Azure AD, OneLogin等)

作者: AI Assistant
创建日期: 2026-05-10
版本: 1.0.0
"""

import base64
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import hashlib
import uuid

# SAML依赖（实际部署时需要安装）
# from onelogin.saml2.auth import OneLogin_Saml2_Auth
# from onelogin.saml2.settings import OneLogin_Saml2_Settings

class SSOProviderType(str, Enum):
    """SSO提供商类型"""
    OKTA = "okta"
    AZURE_AD = "azure_ad"
    ONELOGIN = "onelogin"
    PING_IDENTITY = "ping_identity"
    CUSTOM = "custom"

@dataclass
class SAMLConfig:
    """SAML配置"""
    entity_id: str
    sso_url: str
    slo_url: Optional[str] = None
    x509_cert: Optional[str] = None
    metadata_url: Optional[str] = None
    
    # SP配置
    sp_entity_id: str = "content2revenue-ai"
    sp_acs_url: str = "https://api.content2revenue.com/auth/saml/acs"
    sp_sls_url: str = "https://api.content2revenue.com/auth/saml/sls"
    
    # 高级配置
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    authn_context: str = "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"
    
    # 属性映射
    attribute_mapping: Dict[str, str] = None
    
    def __post_init__(self):
        if self.attribute_mapping is None:
            self.attribute_mapping = {
                "email": "email",
                "first_name": "firstName",
                "last_name": "lastName",
                "groups": "groups",
                "department": "department"
            }

@dataclass
class SAMLUser:
    """SAML认证用户"""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    groups: List[str] = None
    department: Optional[str] = None
    saml_name_id: Optional[str] = None
    saml_session_index: Optional[str] = None
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = []
        if self.attributes is None:
            self.attributes = {}
    
    @property
    def full_name(self) -> str:
        """获取全名"""
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) or self.email

class SAMLProvider:
    """SAML 2.0 身份提供商"""
    
    def __init__(self, config: SAMLConfig):
        self.config = config
        self._settings = None
    
    def _get_settings(self) -> Dict[str, Any]:
        """获取SAML设置"""
        return {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": self.config.sp_entity_id,
                "assertionConsumerService": {
                    "url": self.config.sp_acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": self.config.sp_sls_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "NameIDFormat": self.config.name_id_format,
                "x509cert": "",  # SP证书（可选）
                "privateKey": ""  # SP私钥（可选）
            },
            "idp": {
                "entityId": self.config.entity_id,
                "singleSignOnService": {
                    "url": self.config.sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "singleLogoutService": {
                    "url": self.config.slo_url or self.config.sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": self.config.x509_cert or ""
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": False,
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "signMetadata": False,
                "wantAssertionsSigned": True,
                "wantAssertionsEncrypted": False,
                "wantNameId": True,
                "wantNameIdEncrypted": False,
                "requestedAuthnContext": True,
                "requestedAuthnContextComparison": "exact",
                "wantXMLValidation": True,
                "relaxDestinationValidation": False,
                "destinationStrictlyMatches": False,
                "allowRepeatAttributeName": False,
                "rejectUnsolicitedResponsesWithInResponseTo": False,
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256"
            }
        }
    
    def generate_authn_request(self, return_to: Optional[str] = None) -> Dict[str, str]:
        """
        生成SAML认证请求
        
        Returns:
            {
                "url": "IdP登录URL",
                "saml_request": "SAMLRequest参数",
                "relay_state": "RelayState参数"
            }
        """
        # 生成SAML Request
        request_id = f"_{uuid.uuid4()}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        saml_request_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                    ID="{request_id}"
                    Version="2.0"
                    IssueInstant="{issue_instant}"
                    Destination="{self.config.sso_url}"
                    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                    AssertionConsumerServiceURL="{self.config.sp_acs_url}">
    <saml:Issuer>{self.config.sp_entity_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="{self.config.name_id_format}" AllowCreate="true"/>
    <samlp:RequestedAuthnContext Comparison="exact">
        <saml:AuthnContextClassRef>{self.config.authn_context}</saml:AuthnContextClassRef>
    </samlp:RequestedAuthnContext>
</samlp:AuthnRequest>"""
        
        # Base64编码并URL编码
        saml_request_encoded = base64.b64encode(
            saml_request_xml.encode('utf-8')
        ).decode('utf-8')
        
        import urllib.parse
        saml_request_param = urllib.parse.quote(saml_request_encoded)
        
        relay_state = return_to or "/"
        
        # 构建完整URL
        separator = "&" if "?" in self.config.sso_url else "?"
        login_url = f"{self.config.sso_url}{separator}SAMLRequest={saml_request_param}&RelayState={urllib.parse.quote(relay_state)}"
        
        return {
            "url": login_url,
            "saml_request": saml_request_encoded,
            "relay_state": relay_state,
            "request_id": request_id
        }
    
    def process_saml_response(self, saml_response: str, relay_state: Optional[str] = None) -> SAMLUser:
        """
        处理SAML响应
        
        Args:
            saml_response: Base64编码的SAML Response
            relay_state: 可选的RelayState
            
        Returns:
            SAMLUser对象
        """
        # 解码SAML Response
        try:
            response_xml = base64.b64decode(saml_response).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Invalid SAML response: {e}")
        
        # 解析XML
        root = ET.fromstring(response_xml)
        
        # 命名空间
        ns = {
            'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
            'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol'
        }
        
        # 提取Assertion
        assertion = root.find('.//saml:Assertion', ns)
        if assertion is None:
            raise ValueError("SAML Assertion not found")
        
        # 提取Subject/NameID
        name_id_elem = assertion.find('.//saml:NameID', ns)
        name_id = name_id_elem.text if name_id_elem is not None else None
        
        # 提取属性
        attribute_statement = assertion.find('.//saml:AttributeStatement', ns)
        attributes = {}
        
        if attribute_statement is not None:
            for attr in attribute_statement.findall('saml:Attribute', ns):
                attr_name = attr.get('Name')
                attr_values = []
                for val in attr.findall('saml:AttributeValue', ns):
                    attr_values.append(val.text)
                attributes[attr_name] = attr_values[0] if len(attr_values) == 1 else attr_values
        
        # 映射属性
        mapping = self.config.attribute_mapping
        
        email = attributes.get(mapping.get('email', 'email'), name_id)
        first_name = attributes.get(mapping.get('first_name', 'firstName'))
        last_name = attributes.get(mapping.get('last_name', 'lastName'))
        groups = attributes.get(mapping.get('groups', 'groups'), [])
        if isinstance(groups, str):
            groups = [g.strip() for g in groups.split(',')]
        department = attributes.get(mapping.get('department', 'department'))
        
        return SAMLUser(
            email=email,
            first_name=first_name,
            last_name=last_name,
            groups=groups,
            department=department,
            saml_name_id=name_id,
            attributes=attributes
        )
    
    def generate_metadata(self) -> str:
        """生成SP元数据XML"""
        valid_until = (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     validUntil="{valid_until}"
                     cacheDuration="PT604800S"
                     entityID="{self.config.sp_entity_id}">
    <md:SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="true" protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:NameIDFormat>{self.config.name_id_format}</md:NameIDFormat>
        <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                     Location="{self.config.sp_acs_url}"
                                     index="1"
                                     isDefault="true"/>
        <md:AttributeConsumingService index="1">
            <md:ServiceName xml:lang="en">Content2Revenue AI</md:ServiceName>
            <md:RequestedAttribute Name="email" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic" isRequired="true"/>
            <md:RequestedAttribute Name="firstName" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic"/>
            <md:RequestedAttribute Name="lastName" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic"/>
        </md:AttributeConsumingService>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
        
        return metadata


class SSOConfigManager:
    """SSO配置管理器"""
    
    def __init__(self):
        self._configs: Dict[str, SAMLConfig] = {}
    
    def register_provider(self, tenant_id: str, config: SAMLConfig) -> None:
        """注册SSO提供商"""
        self._configs[tenant_id] = config
    
    def get_provider(self, tenant_id: str) -> Optional[SAMLProvider]:
        """获取SSO提供商"""
        config = self._configs.get(tenant_id)
        if config:
            return SAMLProvider(config)
        return None
    
    def remove_provider(self, tenant_id: str) -> None:
        """移除SSO提供商"""
        self._configs.pop(tenant_id, None)
    
    def list_providers(self) -> Dict[str, SAMLConfig]:
        """列出所有SSO配置"""
        return self._configs.copy()


# 全局SSO配置管理器
sso_config_manager = SSOConfigManager()


def create_saml_config_from_metadata(metadata_xml: str, **kwargs) -> SAMLConfig:
    """
    从IdP元数据创建SAML配置
    
    Args:
        metadata_xml: IdP元数据XML
        **kwargs: 额外的配置参数
        
    Returns:
        SAMLConfig对象
    """
    root = ET.fromstring(metadata_xml)
    ns = {'md': 'urn:oasis:names:tc:SAML:2.0:metadata'}
    
    # 提取entityID
    entity_id = root.get('entityID')
    
    # 提取SSO URL
    sso_service = root.find('.//md:SingleSignOnService[@Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"]', ns)
    sso_url = sso_service.get('Location') if sso_service is not None else None
    
    # 提取SLO URL
    slo_service = root.find('.//md:SingleLogoutService', ns)
    slo_url = slo_service.get('Location') if slo_service is not None else None
    
    # 提取X509证书
    cert_elem = root.find('.//md:X509Certificate', ns)
    x509_cert = cert_elem.text if cert_elem is not None else None
    
    return SAMLConfig(
        entity_id=entity_id,
        sso_url=sso_url,
        slo_url=slo_url,
        x509_cert=x509_cert,
        **kwargs
    )