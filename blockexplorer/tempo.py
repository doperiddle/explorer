"""
Tempo blockchain integration for the BlockCypher explorer.

Tempo is an EVM-compatible Layer 1 blockchain designed for stablecoin payments
(Chain ID: 4217, https://explore.tempo.xyz).
"""

import requests
from datetime import datetime, timezone

from blockcypher.constants import COIN_SYMBOL_MAPPINGS

TEMPO_COIN_SYMBOL = 'tempo'
TEMPO_RPC_URL = 'https://tempo-mainnet.drpc.org'
TEMPO_CHAIN_ID = 4217
TEMPO_SAMPLE_ADDRESS = '0xf333907BaF09DC58ad4Ba39Af94009801C825531'
TEMPO_EXPLORER_URL = 'https://explore.tempo.xyz'

TEMPO_COIN_DATA = {
    'display_name': 'Tempo',
    'display_shortname': 'TEMPO',
    'blockcypher_code': 'tempo',
    'blockcypher_network': 'main',
    'currency_abbrev': 'USD',
    'pow': 'ethash',
    'example_address': TEMPO_SAMPLE_ADDRESS,
    'address_first_char_list': ['0'],
    'singlesig_prefix_list': ['0'],
    'multisig_prefix_list': ['0'],
    'bech32_prefix': 'none',
    'first4_mprv': 'none',
    'first4_mpub': 'none',
    'vbyte_pubkey': 0,
    'vbyte_script': 0,
}

# Patch COIN_SYMBOL_MAPPINGS in-place so all code that imports it sees Tempo
COIN_SYMBOL_MAPPINGS[TEMPO_COIN_SYMBOL] = TEMPO_COIN_DATA

# Extend COIN_CHOICES from blockcypher.constants as well
try:
    from blockcypher.constants import COIN_CHOICES
    if (TEMPO_COIN_SYMBOL, 'Tempo') not in COIN_CHOICES:
        COIN_CHOICES.append((TEMPO_COIN_SYMBOL, 'Tempo'))
except (ImportError, AttributeError):
    pass


def _rpc_call(method, params=None):
    """Make a JSON-RPC call to the Tempo blockchain."""
    if params is None:
        params = []
    payload = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1,
    }
    try:
        response = requests.post(
            TEMPO_RPC_URL,
            json=payload,
            timeout=10,
            headers={'Content-Type': 'application/json'},
        )
        response.raise_for_status()
        data = response.json()
        if 'error' in data:
            return {'error': data['error'].get('message', 'Unknown RPC error')}
        return data.get('result')
    except requests.exceptions.Timeout:
        return {'error': 'Tempo RPC request timed out'}
    except requests.exceptions.RequestException as exc:
        return {'error': str(exc)}


def get_latest_block_number():
    """Return the latest block number as an integer, or None on error."""
    result = _rpc_call('eth_blockNumber')
    if isinstance(result, dict) and 'error' in result:
        return None
    try:
        return int(result, 16)
    except (TypeError, ValueError):
        return None


def get_block_by_number(block_number, include_txs=True):
    """Return the block dict for the given number, or None on error."""
    if isinstance(block_number, int):
        block_param = hex(block_number)
    else:
        block_param = block_number
    result = _rpc_call('eth_getBlockByNumber', [block_param, include_txs])
    if not result or (isinstance(result, dict) and 'error' in result):
        return None
    return result


def get_block_by_hash(block_hash, include_txs=True):
    """Return the block dict for the given hash, or None on error."""
    if not block_hash.startswith('0x'):
        block_hash = '0x' + block_hash
    result = _rpc_call('eth_getBlockByHash', [block_hash, include_txs])
    if not result or (isinstance(result, dict) and 'error' in result):
        return None
    return result


def get_balance_wei(address):
    """Return the address balance in wei (integer), or 0 on error."""
    if not address.startswith('0x'):
        address = '0x' + address
    result = _rpc_call('eth_getBalance', [address, 'latest'])
    if isinstance(result, dict) and 'error' in result:
        return 0
    try:
        return int(result, 16)
    except (TypeError, ValueError):
        return 0


def get_transaction_count(address):
    """Return the number of transactions sent from address, or 0 on error."""
    if not address.startswith('0x'):
        address = '0x' + address
    result = _rpc_call('eth_getTransactionCount', [address, 'latest'])
    if isinstance(result, dict) and 'error' in result:
        return 0
    try:
        return int(result, 16)
    except (TypeError, ValueError):
        return 0


def get_transaction_by_hash(tx_hash):
    """Return the transaction dict, or an error dict."""
    if not tx_hash.startswith('0x'):
        tx_hash = '0x' + tx_hash
    result = _rpc_call('eth_getTransactionByHash', [tx_hash])
    if not result:
        return {'error': 'Transaction not found'}
    if isinstance(result, dict) and 'error' in result:
        return result
    return result


def get_transaction_receipt(tx_hash):
    """Return the transaction receipt dict, or None on error."""
    if not tx_hash.startswith('0x'):
        tx_hash = '0x' + tx_hash
    result = _rpc_call('eth_getTransactionReceipt', [tx_hash])
    if not result or (isinstance(result, dict) and 'error' in result):
        return None
    return result


def get_gas_price_wei():
    """Return the current gas price in wei (integer), or 0 on error."""
    result = _rpc_call('eth_gasPrice')
    if isinstance(result, dict) and 'error' in result:
        return 0
    try:
        return int(result, 16)
    except (TypeError, ValueError):
        return 0


def _hex_to_int(value, default=0):
    """Safely convert a hex string to int."""
    if value is None:
        return default
    try:
        return int(value, 16)
    except (TypeError, ValueError):
        return default


def format_block_for_overview(block):
    """Convert a Tempo JSON-RPC block dict to the shape expected by coin_overview.html."""
    if not block:
        return None
    timestamp = _hex_to_int(block.get('timestamp'))
    txs = block.get('transactions', [])
    total_value = sum(
        _hex_to_int(tx.get('value') if isinstance(tx, dict) else None)
        for tx in txs
    )
    gas_used = _hex_to_int(block.get('gasUsed'))
    size = _hex_to_int(block.get('size'))
    height = _hex_to_int(block.get('number'))
    return {
        'height': height,
        'received_time': datetime.fromtimestamp(timestamp, tz=timezone.utc),
        'n_tx': len(txs),
        'total': total_value,
        'fees': gas_used,
        'size': size,
        'hash': block.get('hash', ''),
    }


def get_recent_blocks(count=5):
    """Return a list of the most recent *count* blocks formatted for the template."""
    latest = get_latest_block_number()
    if latest is None:
        return []
    blocks = []
    for n in range(latest, max(latest - count, -1), -1):
        raw = get_block_by_number(n, include_txs=True)
        formatted = format_block_for_overview(raw)
        if formatted:
            blocks.append(formatted)
    return blocks


def get_fee_estimates():
    """Return a fee-estimate dict shaped like BlockCypher's get_blockchain_fee_estimates()."""
    gas_price = get_gas_price_wei()
    # Convert wei to a per-KB equivalent for template compatibility.
    # Use gas_price * 21000 (typical transfer) as a reasonable fee proxy.
    typical_fee = gas_price * 21000
    return {
        'high_fee_per_kb': typical_fee,
        'medium_fee_per_kb': typical_fee,
        'low_fee_per_kb': typical_fee,
        'high_fee_per_kb__smalltx': typical_fee // 4,
        'medium_fee_per_kb__smalltx': typical_fee // 4,
        'low_fee_per_kb__smalltx': typical_fee // 4,
    }


def get_address_details(address):
    """
    Return an address-details dict shaped like BlockCypher's get_address_full() response.
    Transaction history is not available without an indexer, so flattened_txs is empty.
    """
    if not address.startswith('0x'):
        address_for_rpc = '0x' + address
    else:
        address_for_rpc = address

    balance_wei = get_balance_wei(address_for_rpc)
    n_tx = get_transaction_count(address_for_rpc)

    return {
        'balance': balance_wei,
        'unconfirmed_balance': 0,
        'final_balance': balance_wei,
        'total_sent': 0,
        'total_received': balance_wei,
        'n_tx': n_tx,
        'unconfirmed_n_tx': 0,
        'final_n_tx': n_tx,
        'txs': [],
        'hasMore': False,
    }


def get_transaction_details(tx_hash):
    """
    Return a transaction-details dict shaped for the transaction_overview template.
    """
    tx = get_transaction_by_hash(tx_hash)
    if 'error' in tx:
        return {'error': tx['error']}

    receipt = get_transaction_receipt(tx_hash)
    confirmed = receipt is not None

    block_height = None
    block_hash = None
    if tx.get('blockNumber'):
        block_height = _hex_to_int(tx['blockNumber'])
        block_hash = tx.get('blockHash', '')

    value_wei = _hex_to_int(tx.get('value'))
    gas_used = _hex_to_int(receipt.get('gasUsed') if receipt else None)
    gas_price = _hex_to_int(tx.get('gasPrice'))
    fee_wei = gas_used * gas_price if gas_used and gas_price else 0

    from_addr = tx.get('from', '')
    to_addr = tx.get('to', '') or ''

    inputs = [{'addresses': [from_addr], 'output_value': value_wei + fee_wei}] if from_addr else []
    outputs = [{'addresses': [to_addr], 'value': value_wei}] if to_addr else []

    return {
        'hash': (tx.get('hash', '') or '').lstrip('0x'),
        'block_height': block_height,
        'block_hash': (block_hash or '').lstrip('0x'),
        'confirmed': confirmed,
        'confirmations': 1 if confirmed else 0,
        'total': value_wei,
        'fees': fee_wei,
        'preference': 'medium',
        'inputs': inputs,
        'outputs': outputs,
        'received': datetime.now(tz=timezone.utc),
        'double_spend': False,
        'error': None,
    }


def get_block_details(block_representation):
    """
    Return a block-details dict shaped for the block_overview template.
    block_representation may be a block hash (0x-prefixed hex) or integer height.
    """
    if isinstance(block_representation, int):
        raw = get_block_by_number(block_representation, include_txs=True)
    elif block_representation.startswith('0x') or len(block_representation) == 64:
        raw = get_block_by_hash(block_representation, include_txs=True)
    else:
        try:
            raw = get_block_by_number(int(block_representation), include_txs=True)
        except ValueError:
            raw = get_block_by_hash(block_representation, include_txs=True)

    if not raw:
        return {'error': 'Block not found'}

    txs = raw.get('transactions', [])
    tx_hashes = [
        (tx.get('hash', '') or '').lstrip('0x')
        for tx in txs
        if isinstance(tx, dict)
    ]

    timestamp = _hex_to_int(raw.get('timestamp'))
    height = _hex_to_int(raw.get('number'))
    total_value = sum(_hex_to_int(tx.get('value') if isinstance(tx, dict) else None) for tx in txs)
    gas_used = _hex_to_int(raw.get('gasUsed'))
    size = _hex_to_int(raw.get('size'))

    return {
        'hash': (raw.get('hash', '') or '').lstrip('0x'),
        'height': height,
        'time': datetime.fromtimestamp(timestamp, tz=timezone.utc),
        'n_tx': len(txs),
        'total': total_value,
        'fees': gas_used,
        'size': size,
        'txids': tx_hashes,
        'prev_block': (raw.get('parentHash', '') or '').lstrip('0x'),
    }
